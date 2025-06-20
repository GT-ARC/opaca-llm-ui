import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type

from openai import AsyncOpenAI
from openai.lib import ResponseFormatT
from pydantic import ValidationError
from starlette.websockets import WebSocket

from .models import ConfigParameter, SessionData, Response, AgentMessage, ChatMessage
from .utils import transform_schema

logger = logging.getLogger("src.models")


class AbstractMethod(ABC):
    NAME: str

    @property
    @abstractmethod
    def config_schema(self) -> Dict[str, ConfigParameter]:
        pass

    async def init_models(self, session: SessionData) -> None:
        """
        Initializes and caches single model instance based on the config parameter 'vllm_base_url'.
        The GPT model family can use the same instance (gpt, o1, o3, ...).
        Models are cached within the session data linked to a unique user.

        :param session: The current session data of a unique user
        """
        # Initialize either OpenAI model or vllm model
        base_url = session.config.get(self.NAME, self.default_config())["vllm_base_url"]
        if base_url not in session.llm_clients.keys():
            if base_url == "gpt":
                session.llm_clients[base_url] = AsyncOpenAI()  # Uses api key stored in OPENAI_API_KEY
            else:
                session.llm_clients[base_url] = AsyncOpenAI(api_key=os.getenv("VLLM_API_KEY"), base_url=base_url)


    def default_config(self):
        def extract_defaults(schema):
            # Extracts the default values of nested configurations
            if isinstance(schema, ConfigParameter):
                if schema.type == 'object' and isinstance(schema.default, dict):
                    return {key: extract_defaults(value) for key, value in schema.default.items()}
                else:
                    return schema.default
            else:
                return schema

        return {key: extract_defaults(value) for key, value in self.config_schema.items()}

    @abstractmethod
    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        pass


    async def call_llm(
            self,
            client: AsyncOpenAI,
            model: str,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            temperature: Optional[float] = .0,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            response_format: Optional[Type[ResponseFormatT]] = None,
            guided_choice: Optional[List[str]] = None,
            websocket: Optional[WebSocket] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters. Optionally streams intermediate results
        via the provided websocket. Returns the complete response as an AgentMessage.

        Args:
            client (AsyncOpenAI): An already initialized AsyncOpenAI instance.
            model (str): The name of the model to call.
            agent (str): The name of the agent which got invoked.
            system_prompt (str): The system prompt for the model.
            messages (List[ChatMessage]): The list of messages to call the model with.
            temperature (float): The temperature to pass to the model
            tools (List[Dict[str, Any]]): The list of tools to pass to the model
            tool_choice (Optional[str]): Set the behavior of tool generation.
            response_format (Optional[Dict]): The output schema the model should answer in.
            guided_choice (Optional[List[str]]): A list of choices the LLM should choose between.
            websocket (WebSocket): The websocket to use for streaming intermediate results.

        Returns:
            AgentMessage: The AgentMessage instance representing the response.
        """

        # Initialize variables
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''

        # Initialize agent message
        agent_message = AgentMessage(
            agent=agent,
            content='',
            tools=[]
        )

        # Set settings for model invocation
        kwargs = {
            'model': model,
            'messages': [{"role": "system", "content": system_prompt}] + messages,
            'tools': tools or [],
            'tool_choice': tool_choice if tools else 'none',
        }

        # o1/o3 don't support temperature param
        if not model.startswith(('o1', 'o3')):
            kwargs['temperature'] = temperature

        # There is currently no token streaming available when using built-in response format
        if response_format:
            if self._is_gpt(model):
                completion = await client.beta.chat.completions.parse(**kwargs, response_format=response_format)
                content = completion.choices[0].message.content
                agent_message.formatted_output = completion.choices[0].message.parsed
            else:
                guided_json = transform_schema(response_format.model_json_schema())
                kwargs['extra_body'] = {'guided_json': guided_json}
                kwargs['messages'][0]['content'] += (f"\nYou MUST provide your response as a JSON object that follows "
                                                  f"this schema. Your response must include ALL required fields.\n\n"
                                                  f"Schema:\n{json.dumps(guided_json, indent=2)}\nDO NOT return "
                                                  f"the schema itself. Return a valid JSON object matching the schema.")
                completion = await client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content
                cleaned_content = self.extract_json_like_content(content)
                try:
                    agent_message.formatted_output = response_format.model_validate_json(cleaned_content)
                except ValidationError:
                    agent_message.formatted_output = {}
            agent_message.response_metadata = completion.usage.to_dict()
        else:
            if guided_choice:
                if self._is_gpt(model):
                    kwargs['messages'][0]['content'] += (
                        f"\nYou MUST select one AND ONLY ONE of these choices to answer "
                        f"the request:\n\n {json.dumps(guided_choice, indent=2)} \n\n "
                        f"ONLY ANSWER WITH THE CHOICE AND NOTHING ELSE!")
                else:
                    kwargs["extra_body"] = {"guided_choice": guided_choice}

            # Enable streaming and include token usage
            kwargs['stream'] = True
            kwargs['stream_options'] = {'include_usage': True}

            completion = await client.chat.completions.create(**kwargs)
            async for chunk in completion:

                # Usage is present in the last chunk so break once it is available
                if usage := chunk.usage:
                    agent_message.response_metadata = usage.to_dict()
                    break

                choice = chunk.choices[0].delta
                tool_calls = choice.tool_calls

                if tool_calls:
                    for tool_call in tool_calls:
                        tool_call_id = tool_call.id

                        if tool_call_id:
                            tool_call_buffers[tool_call_id] = {
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments or '',
                            }
                        else:
                            last_tool_call = next(reversed(tool_call_buffers.values()), None)
                            if last_tool_call:
                                # If the full arguments were generated (happens in mistral models)
                                # then set the arguments rather than append to them
                                if model.startswith(('gpt', 'o1', 'o3')):
                                    last_tool_call['arguments'] += tool_call.function.arguments or ''
                                else:
                                    try:
                                        json.loads(tool_call.function.arguments)
                                        last_tool_call['arguments'] = tool_call.function.arguments
                                    except json.JSONDecodeError:
                                        last_tool_call['arguments'] += tool_call.function.arguments or ''

                    agent_message.tools = [
                        {
                            'id': i,
                            'name': function['name'],
                            'args': function['arguments'],
                            'result': '',
                        }
                        for i, function in enumerate(tool_call_buffers.values())
                    ]
                else:
                    agent_message.content = choice.content or ''
                    content += choice.content or ''
                if websocket:
                    await websocket.send_json(agent_message.model_dump_json())

        # Transform generated arguments into JSON
        for tool in agent_message.tools:
            try:
                tool['args'] = json.loads(tool['args'])
            except json.JSONDecodeError:
                tool['args'] = {}
            if not tool["args"]:
                tool["args"] = {}
                continue

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        if websocket:
            agent_message.content = ''
            await websocket.send_json(agent_message.model_dump_json())

        agent_message.content = content

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message
    
    async def call_llm_with_pdf(
        self,
        client: AsyncOpenAI,
        model: str,
        agent: str,
        system_prompt: str,
        user_question: str,
        pdf_file_path: str,
        temperature: Optional[float] = 0.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        response_format: Optional[Type[ResponseFormatT]] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with a PDF file input and an accompanying user question.
        Uses OpenAI's file upload + input_file mechanism.

        Args:
            client (AsyncOpenAI): An initialized OpenAI client.
            model (str): The model name.
            agent (str): The agent name.
            system_prompt (str): The system prompt.
            user_question (str): The question to ask about the PDF.
            pdf_file_path (str): Path to the local PDF file to upload.
            temperature (float): Temperature for sampling.
            tools (List): Tool definitions if any.
            tool_choice (str): Tool choice policy.
            response_format (Type): Optional pydantic schema for parsing.

        Returns:
            AgentMessage: Standard response object.
        """

        exec_time = time.time()

        agent_message = AgentMessage(
            agent=agent,
            content='',
            tools=[]
        )

        logger.info(f"model type: {model}")


        # --- STEP 1: Upload PDF ---
        uploaded_file = await client.files.create(
            file=open(pdf_file_path, "rb"),
            purpose="assistants"
        )

        logger.info("file upload status:")
        logger.info(uploaded_file.status)
        logger.info(f"Uploaded file ID: {uploaded_file.id}")
        logger.info(f"Uploaded file details: {uploaded_file}")

        # --- STEP 2: Build proper messages ---
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "file": {"file_id": uploaded_file.id}
                    },
                    {
                        "type": "text",
                        "text": user_question
                    }
                ]
            }
        ]

        # --- STEP 3: Prepare kwargs ---
        kwargs = {
            "model": model,
            "messages": messages,
            "tools": tools or [],
            "tool_choice": tool_choice if tools else "none"
        }

        if not model.startswith(("o1", "o3")):
            kwargs["temperature"] = temperature

        # --- STEP 4: Call the LLM with or without response_format ---
        if response_format:
            logger.info("response_format present")
            if self._is_gpt(model):
                completion = await client.beta.chat.completions.parse(
                    **kwargs, response_format=response_format
                )
                agent_message.content = completion.choices[0].message.content
                agent_message.formatted_output = completion.choices[0].message.parsed
            else:
                # For non-GPT models: fallback
                guided_json = transform_schema(response_format.model_json_schema())
                kwargs["extra_body"] = {"guided_json": guided_json}
                kwargs["messages"][0]["content"] += (
                    f"\nYou MUST respond as JSON matching this schema:\n{json.dumps(guided_json, indent=2)}"
                )
                completion = await client.chat.completions.create(**kwargs)
                raw_content = completion.choices[0].message.content
                cleaned = self.extract_json_like_content(raw_content)
                try:
                    agent_message.formatted_output = response_format.model_validate_json(cleaned)
                except ValidationError:
                    agent_message.formatted_output = {}
                agent_message.content = raw_content
            agent_message.response_metadata = completion.usage.to_dict()
        else:
            logger.info("no response-format")
            completion = await client.chat.completions.create(**kwargs)
            # no streaming here: just grab the single-shot response
            agent_message.content = completion.choices[0].message.content
            agent_message.response_metadata = completion.usage.to_dict()

        agent_message.execution_time = time.time() - exec_time

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output,
                    extra={"agent_name": agent})

        return agent_message

    @staticmethod
    def _is_gpt(model: str):
        return True if model.startswith(('o1', 'o3', 'gpt')) else False

    @staticmethod
    def extract_json_like_content(text):
        """Removes any string content before the first { and after the last }"""
        match = re.search(r'\{.*}', text, re.DOTALL)
        return match.group(0) if match else text
