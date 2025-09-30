import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type

from pydantic import BaseModel
from starlette.websockets import WebSocket

from .models import ConfigParameter, SessionData, QueryResponse, AgentMessage, ChatMessage, OpacaException, Chat, ToolCall, get_supported_models
from .utils import transform_schema, openapi_to_functions
from .file_utils import upload_files

logger = logging.getLogger(__name__)


class AbstractMethod(ABC):
    NAME: str

    def __init__(self, session: SessionData, websocket: WebSocket | None):
        self.session = session
        self.websocket = websocket

    @classmethod
    def config_schema(cls) -> Dict[str, ConfigParameter]:
        pass

    @staticmethod
    def make_llm_config_param(name: Optional[str] = None, description: Optional[str] = None):
        models = [f"{url}::{model}" for url, _, models in get_supported_models() for model in models]
        return ConfigParameter(
            name=name,
            description=description,
            type="string",
            required=True,
            default=models[0],
            enum=models,
            free_input=True,
        )

    @classmethod
    def default_config(cls):
        def extract_defaults(schema):
            # Extracts the default values of nested configurations
            if isinstance(schema, ConfigParameter):
                if schema.type == 'object' and isinstance(schema.default, dict):
                    return {key: extract_defaults(value) for key, value in schema.default.items()}
                else:
                    return schema.default
            else:
                return schema

        return {key: extract_defaults(value) for key, value in cls.config_schema().items()}


    async def query(self, message: str, chat: Chat) -> QueryResponse:
        return await self.query_stream(message, chat)

    @abstractmethod
    async def query_stream(self, message: str, chat: Chat) -> QueryResponse:
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
            response_format: Optional[Type[BaseModel]] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
            session (SessionData): The current session
            model (str): LLM host AND model name (e.g., "https://...: gpt-4-turbo"), from config.
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt to start the conversation.
            messages (List[ChatMessage]): The list of chat messages.
            temperature (float): The model temperature to use.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", or tool name).
            response_format (Optional[Type[BaseModel]]): Optional Pydantic schema to validate response.
            websocket (Optional[WebSocket]): WebSocket to stream output to frontend.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """
        try:
            url, model = map(str.strip, model.split("::"))
        except Exception:
            raise Exception(f"Invalid format: Must be '<llm-host>::<model>': {model}")
        client = await self.session.get_llm_client(url)

        # Initialize variables
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        file_message_parts = await upload_files(self.session, url)

        # Modify the last user message to include file parts
        if file_message_parts:
            messages[-1].content = [*file_message_parts, {"type": "input_text", "text": messages[-1].content}]

        # Set a custom response format schema if provided, else expect plain text
        r_format = transform_schema(response_format.model_json_schema()) if response_format else \
            {'format': {'type': 'text'}}

        # Set settings for model invocation
        kwargs = {
            'model': model,
            'input': [ChatMessage(role="system", content=system_prompt), *messages],
            'tools': tools or [],
            'tool_choice': tool_choice if tools else 'none',
            'text': r_format,
            'stream': True
        }

        if response_format:
            kwargs['text'] = transform_schema(response_format.model_json_schema())

        # o1/o3/o4/gpt-5 don't support temperature param
        if not model.startswith(('o1', 'o3', 'o4', 'gpt-5')):
            kwargs['temperature'] = temperature

        # Main stream logic
        stream = await client.responses.create(**kwargs)
        async for event in stream:

            # New tool call generation started, including the complete function call name
            if event.type == 'response.output_item.added' and event.item.type == 'function_call':
                agent_message.tools.append(ToolCall(name=event.item.name, id=event.output_index))
                tool_call_buffers[event.output_index] = ""

            # Tool call argument chunk received
            elif event.type == 'response.function_call_arguments.delta':
                # We assume that the entry has been created already
                tool_call_buffers[event.output_index] += event.delta

            # Plain text chunk received
            elif event.type == 'response.output_text.delta':
                agent_message.content = event.delta
                content += event.delta

            # Final message received
            elif event.type == 'response.completed':
                # If a response format was provided, try to cast the response to the provided schema
                if response_format:
                    try:
                        agent_message.formatted_output = response_format.model_validate_json(content)
                    except json.decoder.JSONDecodeError:
                        raise OpacaException("An error occurred while parsing a response JSON", error_message="An error occurred while parsing a response JSON", status_code=500)
                # Capture token usage
                agent_message.response_metadata = event.response.usage.to_dict()

            # Final tool call chunk received
            elif event.type == 'response.function_call_arguments.done':
                # Get the tool index from the event output index
                tool_idx = next((t.id for t in agent_message.tools if t.id == event.output_index), -1)
                # Try to transform function arguments into JSON
                try:
                    agent_message.tools[tool_idx].args = json.loads(tool_call_buffers[event.output_index])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse tool arguments: {tool_call_buffers[event.output_index]}")
                    agent_message.tools[tool_idx].args = {}

            if self.websocket:
                await self.websocket.send_json(agent_message.model_dump_json())
                agent_message.content = ''

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        if self.websocket:
            agent_message.content = ''
            await self.websocket.send_json(agent_message.model_dump_json())

        agent_message.content = content

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message


    @staticmethod
    def _is_gpt(model: str):
        return True if model.startswith(('o1', 'o3', 'gpt')) else False


    async def invoke_tool(self, tool_name: str, tool_args: dict, tool_id: int) -> ToolCall:
        if "--" in tool_name:
            agent_name, action_name = tool_name.split('--', maxsplit=1)
        else:
            agent_name, action_name = None, tool_name

        try:
            t_result = await self.session._opaca_client.invoke_opaca_action(
                action_name,
                agent_name,
                tool_args,
            )
        except Exception as e:
            t_result = f"Failed to invoke tool.\nCause: {e}"

        return ToolCall(id=tool_id, name=tool_name, args=tool_args, result=t_result)


    async def get_tools(self, max_tools=128) -> tuple[list[dict], str]:
        tools, error = openapi_to_functions(await self.session._opaca_client.get_actions_openapi(inline_refs=True))
        if len(tools) > max_tools:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of {max_tools}. All tools after index {max_tools} will be ignored!\n")
            tools = tools[:max_tools]
        return tools, error
