import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type

from openai import AsyncOpenAI
from openai.lib import ResponseFormatT
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
            model: str,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            temperature: Optional[float] = .0,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            vllm_api_key: Optional[str] = os.getenv("VLLM_API_KEY"),
            vllm_base_url: Optional[str] = os.getenv("VLLM_BASE_URL"),
            response_format: Optional[Type[ResponseFormatT]] = None,
            websocket: Optional[WebSocket] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters. Optionally streams intermediate results
        via the provided websocket. Returns the complete response as an AgentMessage.

        Args:
            model (str): The name of the model to call.
            agent (str): The name of the agent which got invoked.
            system_prompt (str): The system prompt for the model.
            messages (List[ChatMessage]): The list of messages to call the model with.
            temperature (float): The temperature to pass to the model
            tools (List[Dict[str, Any]]): The list of tools to pass to the model
            tool_choice (Optional[str]): Set the behavior of tool generation.
            vllm_api_key (Optional[str]): An optional vllm API key when using models within the vllm framework.
            vllm_base_url (Optional[str]): An optional vllm base URL when using models within the vllm framework.
            response_format (Optional[Dict]): An optional output schema the model should answer in.
            websocket (WebSocket): The websocket to use for streaming intermediate results.

        Returns:
            AgentMessage: The AgentMessage instance representing the response.
        """

        # Initialize variables
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''

        # Initialize either OpenAI model or vllm model
        if self._is_gpt(model):
            client = AsyncOpenAI()  # Uses api key stored in OPENAI_API_KEY
        else:
            client = AsyncOpenAI(api_key=vllm_api_key, base_url=vllm_base_url)

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
        }

        # o1/o3 don't support temperature param
        if not model.startswith(('o1', 'o3')):
            kwargs['temperature'] = temperature

        # There is currently no token streaming available when using built-in response format
        if response_format:
            if self._is_gpt(model):
                completion = await client.beta.chat.completions.parse(**kwargs, response_format=response_format)
                agent_message.content = completion.choices[0].message.content
                agent_message.formatted_output = completion.choices[0].message.parsed
            else:
                guided_json = transform_schema(response_format.model_json_schema())
                kwargs['extra_body'] = {'guided_json': guided_json}
                kwargs['messages'][0]['content'] += (f"\nYou MUST provide your response as a JSON object that follows "
                                                  f"this schema. Your response must include ALL required fields.\n\n"
                                                  f"Schema:\n{json.dumps(guided_json, indent=2)}\nDO NOT return "
                                                  f"the schema itself. Return a valid JSON object matching the schema.")
                completion = await client.chat.completions.create(**kwargs)
                agent_message.content = completion.choices[0].message.content
                agent_message.formatted_output = response_format.model_validate_json(agent_message.content)
            agent_message.response_metadata = completion.usage.to_dict()
        else:
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

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        if websocket:
            agent_message.content = ''
            await websocket.send_json(agent_message.model_dump_json())

        agent_message.content = content

        logger.info(agent_message.content or agent_message.tools, extra={"agent_name": agent})

        return agent_message

    @staticmethod
    def _is_gpt(model: str):
        return True if model.startswith(('o1', 'o3', 'gpt')) else False
