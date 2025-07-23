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

from .models import ConfigParameter, SessionData, Response, AgentMessage, ChatMessage
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
        client: AsyncOpenAI,
        model: str,
        agent: str,
        system_prompt: str,
        messages: List[ChatMessage],
        temperature: Optional[float] = 0.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        response_format: Optional[Type[ResponseFormatT]] = None,
        guided_choice: Optional[List[str]] = None,
        websocket: Optional[WebSocket] = None,
        session: Optional[SessionData] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
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
            session (Optional[SessionData]): Session to track uploaded files, etc.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        logger.info(model)

        # Handle uploaded files (PDFs) from session
        file_message_parts = []

        manual_file_id = ""  # <-- Insert a manual file_id here for testing, or leave empty ""

        file_ids = []

        if manual_file_id:
            logger.info(f"Using manual file_id for testing: {manual_file_id}")
            file_ids.append(manual_file_id)
        else:
            if session and session.uploaded_files:
                # Upload all unsent files
                for filename, filedata in session.uploaded_files.items():
                    file_id = filedata.get("file_id")

                    if not file_id:
                        # Upload the file
                        file_bytes = filedata["content"].getvalue()
                        file_obj = io.BytesIO(file_bytes)
                        file_obj.name = filename  # Required by OpenAI SDK

                        uploaded = await client.files.create(
                            file=file_obj,
                            purpose="assistants"
                        )

                        logger.info(f"Uploaded file ID={uploaded.id} for {filename}")

                        file_id = uploaded.id
                        filedata["file_id"] = file_id
                        filedata["sent"] = True

                    else:
                        logger.info(f"Reusing existing file_id: {file_id} for {filename}")

                    file_ids.append(file_id)

        # Build file message parts for all file_ids
        for fid in file_ids:
            file_message_parts.append({
                "type": "file",
                "file": {"file_id": fid}
            })

        # Now build the full messages list including all prior messages from session.messages
        # For each message in session.messages, add it as is
        # Finally, append the current user message with attached file parts

        full_messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add all prior messages from session (assumed to be dicts with 'role' and 'content')
        for msg in session.messages:
            full_messages.append(msg)

        # Append the current user message with file parts
        #logger.info(messages[-1])
        last_message = messages[-1]

        if isinstance(last_message, dict):
            user_text = last_message.get("content", "")
        else:
            user_text = getattr(last_message, "content", "")

        full_messages.append({
            "role": "user",
            "content": file_message_parts + [{"type": "text", "text": user_text}]
        })

        # Build kwargs for the OpenAI client
        kwargs = {
            "model": model,
            "messages": full_messages,
            "tools": tools or [],
            "tool_choice": tool_choice if tools else "none",
        }

        # o1/o3 don't support temperature param
        if not model.startswith(('o1', 'o3')):
            kwargs["temperature"] = temperature

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
                content = raw_content
            agent_message.response_metadata = completion.usage.to_dict()
        else:
            # Handle tool choice options
            if guided_choice and self._is_gpt(model):
                kwargs["messages"][0]["content"] += (
                    f"\nYou MUST select one AND ONLY ONE of these choices:\n\n{json.dumps(guided_choice, indent=2)}\n\n"
                    f"ONLY ANSWER WITH THE CHOICE AND NOTHING ELSE!"
                )
            elif guided_choice:
                kwargs["extra_body"] = {"guided_choice": guided_choice}

            # Enable streaming and include token usage
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}

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
                        tool_call_buffers[tool_call.id] = {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or '',
                        }
                    agent_message.tools = [
                        {"id": i, "name": fn["name"], "args": fn["arguments"], "result": ''}
                        for i, fn in enumerate(tool_call_buffers.values())
                    ]
                else:
                    chunk_text = choice.content or ''
                    if chunk_text:
                        content += chunk_text
                        agent_message.content = content  # always set full content
                        if websocket:
                            await websocket.send_json(agent_message.model_dump_json())

        # Final response packaging
        for tool in agent_message.tools:
            try:
                tool["args"] = json.loads(tool["args"])
            except json.JSONDecodeError:
                tool["args"] = {}

        agent_message.execution_time = time.time() - exec_time
        agent_message.content = content

        # Final stream to transmit execution time and response metadata
        if websocket:
            await websocket.send_json(agent_message.model_dump_json())

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
