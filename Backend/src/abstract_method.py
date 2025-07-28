import json
import logging
import os
import re
import time
import io
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
import datetime 

from openai import AsyncOpenAI
from openai.lib import ResponseFormatT
from pydantic import ValidationError
from starlette.websockets import WebSocket

from .models import ConfigParameter, SessionData, Response, AgentMessage, ChatMessage, OpacaException
from .utils import transform_schema

logger = logging.getLogger(__name__)


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
            session: SessionData,
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
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
            session (SessionData): The current session
            client (AsyncOpenAI): An already initialized OpenAI client.
            model (str): Model name (e.g., "gpt-4-turbo").
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt to start the conversation.
            messages (List[ChatMessage]): The list of chat messages.
            temperature (float): The model temperature to use.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", or tool name).
            response_format (Optional[Type[ResponseFormatT]]): Optional Pydantic schema to validate response.
            guided_choice (Optional[List[str]]): List of strings for the model to pick from.
            websocket (Optional[WebSocket]): WebSocket to stream output to frontend.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """

        # Initialize variables
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        logger.info(model)

        # Handle uploaded files (PDFs) from session
        file_message_parts = []

        # Set settings for model invocation
        file_ids = []

        # Upload all unsent files
        for filename, filedata in session.uploaded_files.items():
            file_id = filedata.file_id

            if not file_id:
                # Upload the file
                file_bytes = filedata._content.getvalue()   # Access private content
                file_obj = io.BytesIO(file_bytes)
                file_obj.name = filename  # Required by OpenAI SDK

                uploaded = await client.files.create(
                    file=file_obj,
                    purpose="assistants"
                )

                logger.info(f"Uploaded file ID={uploaded.id} for {filename}")

                file_id = uploaded.id              
                filedata.file_id = file_id      # Set attribute
                filedata.sent = True            # Set attribute

            else:
                logger.info(f"Reusing existing file_id: {file_id} for {filename}")

            file_ids.append(file_id)

        for fid in file_ids:
            file_message_parts.append({
                "type": "file",
                "file": {"file_id": fid}
            })

        # Modify the last user message to include file parts
        last_message = messages[-1]

        logger.info(type(last_message))

        # Add user question

        if isinstance(last_message, dict):        
            user_text = last_message["content"]
            last_message["content"] = file_message_parts + [{"type": "text", "text": user_text}]
        else:
            user_text = getattr(last_message, "content", "")
            last_message.content = file_message_parts + [{"type": "text", "text": user_text}]
        
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
        # Handle structured response parsing
        if response_format:
            if self._is_gpt(model):
                completion = await client.beta.chat.completions.parse(
                    **kwargs, response_format=response_format
                )
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
            # Handle tool choice options
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

                if session.abort_sent:
                    raise OpacaException(
                        user_message="(The generation of the response has been stopped.)",
                        error_message="Completion generation aborted by user. See Debug/Logging Tab to see what has been done so far."
                    )

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


    @staticmethod
    def _is_gpt(model: str):
        return True if model.startswith(('o1', 'o3', 'gpt')) else False

    @staticmethod
    def extract_json_like_content(text):
        """Removes any string content before the first { and after the last }"""
        match = re.search(r'\{.*}', text, re.DOTALL)
        return match.group(0) if match else text
