import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Literal
import asyncio
import jsonref
from itertools import count

import httpx
from openai.types.responses import ResponseFunctionToolCall
from pydantic import BaseModel, ValidationError
import litellm
from litellm.types.responses.main import OutputFunctionToolCall
from litellm.types.llms.openai import ResponsesAPIStreamEvents as event_type

from .models import (SessionData, QueryResponse, AgentMessage, ChatMessage, OpacaException, Chat,
                     ToolCall, ContainerLoginNotification, ContainerLoginResponse, ToolCallMessage,
                     ToolResultMessage, TextChunkMessage, MetricsMessage, StatusMessage, MethodConfig,
                     MissingApiKeyNotification, MissingApiKeyResponse)
from .file_utils import upload_files
from .internal_tools import InternalTools, INTERNAL_TOOLS_AGENT_NAME

logger = logging.getLogger(__name__)


class AbstractMethod(ABC):
    NAME: str
    CONFIG: type[MethodConfig]

    def __init__(self, session: SessionData, streaming=False):
        self.session = session
        self.streaming = streaming
        self.tool_counter = count(0)
        self.internal_tools = InternalTools(session, type(self))

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        return cls.CONFIG.model_json_schema(mode='serialization')['properties']

    def get_config(self) -> MethodConfig:
        return self.session.get_config(self)

    @abstractmethod
    async def query(self, message: str, chat: Chat) -> QueryResponse:
        pass

    def next_tool_id(self, agent_message: AgentMessage):
        return f"{agent_message.id}/{next(self.tool_counter)}"

    async def call_llm(
            self,
            model: str,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            temperature: Optional[float] = .0,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Literal["auto", "none", "only", "required"]] = "auto",
            response_format: Optional[Type[BaseModel]] = None,
            status_message: str | None = None,
            is_output: bool = False,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
            model (str): LLM host/provider AND model name (e.g., "openai/gpt-4o-mini"), from config.
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt for model instructions.
            messages (List[ChatMessage]): The list of chat messages.
            temperature (float): The model temperature to use.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", "only", or "required").
            response_format (Optional[Type[BaseModel]]): Optional Pydantic schema to validate response.
            status_message (str): optional message to be streamed to the UI
            is_output (bool): whether agent output should be streamed directly to chat or only to debug

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """

        if status_message:
            await self.send_to_websocket(StatusMessage(agent=agent, status=status_message))

        # Check if an additional API key is required for this model
        if not self.session.get_api_key(model) and not litellm.validate_environment(model).get("keys_in_environment"):
            await self.handle_invalid_api_key(model)

        # Initialize variables
        exec_time = time.time()
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        file_message_parts = await upload_files(self.session, model)

        # Modify the last user message to include file parts
        if file_message_parts:
            messages[-1].content = [*file_message_parts, {"type": "input_text", "text": messages[-1].content}]

        # Set settings for model invocation
        kwargs = {
            'api_key': self.session.get_api_key(model),
            'model': model,
            'instructions': system_prompt,
            'input': [m.model_dump() for m in messages],
            'tools': tools or [],
            'tool_choice': tool_choice if tools else 'none',
            'temperature': temperature,
            'text_format': response_format,
            'stream': True
        }

        # If tool_choice is set to "only", use "auto" for external API call
        if tool_choice == "only":
            kwargs['tool_choice'] = 'auto'

        # Main stream logic
        stream = await litellm.aresponses(**kwargs)
        async for event in stream:

            # Check if an "abort" message has been sent by the user
            if self.session.abort_sent:
                raise OpacaException(
                    user_message="(The generation of the response has been stopped.)",
                    error_message="Completion generation aborted by user. See Debug/Logging Tab to see what has been done so far."
                )

            # Plain text chunk received
            elif event.type == event_type.OUTPUT_TEXT_DELTA:
                if tool_choice == "only":
                    break
                agent_message.content += event.delta
                await self.send_to_websocket(TextChunkMessage(id=agent_message.id, agent=agent, chunk=event.delta, is_output=is_output))

            # Final message received
            elif event.type == event_type.RESPONSE_COMPLETED:
                # If a response format was provided, try to cast the response to the provided schema
                if response_format:
                    try:
                        agent_message.formatted_output = response_format.model_validate_json(agent_message.content)
                    except (json.decoder.JSONDecodeError, ValidationError) as e:
                        raise OpacaException(
                            f"An error occurred while parsing a response JSON. Is model '{model}' supporting structured outputs?",
                            error_message=str(e),
                            status_code=500
                        )

                # Alternative tool output
                for t in event.response.output:
                    if isinstance(t, (OutputFunctionToolCall, ResponseFunctionToolCall)):
                        try:
                            tool = ToolCall(name=t.name, id=self.next_tool_id(agent_message), args=json.loads(t.arguments))
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse tool arguments: {t.arguments}")
                            tool = ToolCall(name=t.name, id=self.next_tool_id(agent_message), args={})
                        agent_message.tools.append(tool)
                        await self.send_to_websocket(ToolCallMessage(id=tool.id, name=tool.name, args=tool.args, agent=agent))
                # Capture token usage
                agent_message.response_metadata = event.response.usage.model_dump()

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        await self.send_to_websocket(MetricsMessage(
            execution_time=agent_message.execution_time,
            metrics=agent_message.response_metadata,
        ))

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message


    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)


    async def invoke_tool(self, tool_name: str, tool_args: dict, tool_id: str, login_attempt_retry: bool = False) -> ToolCall:
        """
        Invoke OPACA action matching the given tool. If invoke fails due to required login, attempt Login (via websocket callback)
        and try again. In any case returns a ToolCall, where "result" can be error message.
        """
        if "--" in tool_name:
            agent_name, action_name = tool_name.split('--', maxsplit=1)
        else:
            agent_name, action_name = None, tool_name

        try:
            if agent_name == INTERNAL_TOOLS_AGENT_NAME:
                t_result = await self.internal_tools.call_internal_tool(action_name, tool_args)
            else:
                t_result = await self.session.opaca_client.invoke_opaca_action(action_name, agent_name, tool_args)
        except httpx.HTTPStatusError as e:
            res = e.response.json()
            t_result = f"Failed to invoke tool.\nStatus code: {e.response.status_code}\nResponse: {e.response.text}\nResponse JSON: {res}"
            cause = res.get("cause", {}).get("message", "")
            status = res.get("cause", {}).get("statusCode", -1)
            if self.session.has_websocket() and (status in [401, 403] or ("401" in cause or "403" in cause or "credentials" in cause)):
                return await self.handleContainerLogin(agent_name, action_name, tool_name, tool_args, tool_id, login_attempt_retry)
        except Exception as e:
            t_result = f"Failed to invoke tool.\nCause: {e}"

        await self.send_to_websocket(ToolResultMessage(id=tool_id, result=t_result))
        return ToolCall(id=tool_id, name=tool_name, args=tool_args, result=t_result)


    async def get_tools(self, max_tools=128) -> tuple[list[dict], str]:
        """
        Get list of available actions as OpenAI Functions. This primarily includes the OPACA actions, but can also include "internal" tools.
        """
        opaca_tools, error = openapi_to_functions(await self.session.opaca_client.get_actions_openapi(inline_refs=True))
        internal_tools = self.internal_tools.get_internal_tools_openai()
        tools = [*opaca_tools, *internal_tools]
        if len(tools) > max_tools:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of {max_tools}. All tools after index {max_tools} will be ignored!\n")
            tools = tools[:max_tools]
        return tools, error


    async def handleContainerLogin(self, agent_name: str, action_name: str, tool_name: str, tool_args: dict, tool_id: str, login_attempt_retry: bool = False):
        """Handles failed tool invocation due to missing credentials."""

        # If a "missing credentials" error is encountered, initiate container login
        container_id, container_name = await self.session.opaca_client.get_most_likely_container_id(agent_name, action_name)

        async with self.session.opaca_client.login_lock:
            # might already be logged in on lock-release if two actions of same container were called in parallel
            if container_id in self.session.opaca_client.logged_in_containers:
                return await self.invoke_tool(tool_name, tool_args, tool_id, True)

            # Get credentials from user
            await self.session.websocket_send(ContainerLoginNotification(
                container_name=container_name,
                tool_name=tool_name,
                retry=login_attempt_retry
            ))
            response = ContainerLoginResponse(**await self.session.websocket_receive())

            # Check if credentials were provided
            if not response.username or not response.password:
                return ToolCall(id=tool_id, name=tool_name, args=tool_args,
                                result=f"Failed to invoke tool.\nNo credentials provided.")

            # Send credentials to container via OPACA
            await self.session.opaca_client.container_login(container_id, response.username, response.password)

        # try to invoke the tool again
        res = await self.invoke_tool(tool_name, tool_args, tool_id, True)

        # Schedule a deferred logout based on the user-provided timeout
        asyncio.create_task(self.session.opaca_client.deferred_container_logout(container_id, response.timeout))

        return res

    async def handle_invalid_api_key(self, model, is_invalid: bool = False):
        await self.send_to_websocket(MissingApiKeyNotification(is_invalid=is_invalid, model=model))
        response = MissingApiKeyResponse(**await self.session.websocket_receive())
        if response.api_key:
            if litellm.check_valid_key(model, response.api_key):
                self.session.set_api_key(model, response.api_key)
            else:
                await self.handle_invalid_api_key(model, True)
        else:
            raise OpacaException(user_message=f"No valid API key was provided for model {model}!")

def openapi_to_functions(openapi_spec, agent: str | None = None):
    """
    Convert OpenAPI REST specification (with inlined references) to OpenAI Function specification.

    Parameters:
    - openapi_spec: the OpenAPI specification
    - agent: name of OPACA agent to filter for, or None for all
    """
    functions = []
    error_msg = ""

    for path, methods in openapi_spec.get("paths", {}).items():
        for method, spec_with_ref in methods.items():
            # Resolve JSON references.
            try:
                spec = jsonref.replace_refs(spec_with_ref)
            except Exception as e:
                error_msg += f'Error while replacing references for unknown action. Cause: {e}\n'
                continue

            # Extract a name for the functions
            try:
                # The operation id is formatted as 'containerId-agentName-actionName'
                container_id, agent_name, function_name = spec.get("operationId").split(';')
                # action relevant for selected agent?
                if agent and agent_name != agent:
                    continue
            except Exception as e:
                error_msg += f'Error while splitting the operation id {spec.get("operationId")}. Cause: {e}\n'
                continue

            # Extract a description and parameters.
            desc = spec.get("description", "")[:1024] or spec.get("summary", "")[:1024]

            # assemble function block
            # structure of schema: type (str), required (list), properties (the actual parameters), additionalProperties (bool)
            schema = (spec.get("requestBody", {})
                        .get("content", {})
                        .get("application/json", {})
                        .get("schema"))
            schema.setdefault("properties", {})  # must be present even if no params

            functions.append(
                {
                    "type": "function",
                    "name": agent_name + '--' + function_name,
                    "description": desc,
                    "parameters": schema,
                }
            )

    return functions, error_msg
