import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from openai import AsyncOpenAI
from starlette.websockets import WebSocket

from .models import ConfigParameter, SessionData, Response, AgentMessage, ChatMessage

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

    @staticmethod
    async def call_llm(
            client: AsyncOpenAI,
            model: str,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            temperature: Optional[float] = .0,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            websocket: WebSocket = None
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
            'tool_choice': tool_choice,
            'stream': True,
            'stream_options': {'include_usage': True},
        }

        # o1/o3 don't support temperature param
        if not model.startswith(("o1", "o3")):
            kwargs['temperature'] = temperature

        #
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

        logger.info(agent_message.content or agent_message.tools, extra={"agent_name": agent})

        return agent_message
