from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Any, Type, Literal
import asyncio
import jsonref
from itertools import count
from datetime import datetime as dt
import os

import httpx
from openai.types.responses import ResponseFunctionToolCall
from pydantic import BaseModel, ValidationError
import litellm
from litellm.experimental_mcp_client.client import MCPClient
from litellm.types.responses.main import OutputFunctionToolCall
from litellm.types.llms.openai import ResponsesAPIStreamEvents as event_type
from mcp.types import CallToolRequestParams

from .models import (ToolApprovalState, SessionData, QueryResponse, AgentMessage, ChatMessage, OpacaException, Chat,
                     ToolCall, ToolType, ContainerLoginNotification, ContainerLoginResponse, ToolCallMessage,
                     ToolResultMessage, TextChunkMessage, MetricsMessage, StatusMessage, MethodConfig,
                     MissingApiKeyNotification, MissingApiKeyResponse, ConfirmActionNotification, ConfirmActionResponse,
                     LLMConfig)
from .file_utils import upload_files
from .opaca_client import actions_blacklist

if TYPE_CHECKING:
    from .internal_tools import InternalTools


# list of string-fragments; if any action or agent name contains one of those, SAGE will ask for confirmation before calling the tool
actions_needing_confirmation: List[str] = []

logger = logging.getLogger(__name__)


class AbstractMethod(ABC):
    NAME: str
    CONFIG: type[MethodConfig]

    def __init__(
            self,
            session: SessionData,
            chat: Chat,
            response: QueryResponse,
            streaming: bool = False,
            internal_tools: InternalTools = None
    ) -> None:
        self.session = session
        self.chat = chat
        self.response = response
        self.streaming = streaming
        self.tool_counter = count(0)
        self.internal_tools = internal_tools
        if self.internal_tools:
            self.internal_tools.set_chat(chat)

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        return cls.CONFIG.model_json_schema(mode='serialization')

    def get_config(self) -> MethodConfig:
        return self.session.get_config(self)

    @abstractmethod
    async def query(self) -> QueryResponse:
        pass

    def next_tool_id(self, agent_message: AgentMessage):
        return f"{agent_message.id}/{next(self.tool_counter)}"

    def _resolve_tool_approval(self, tool: ToolCall) -> ToolApprovalState:
        if tool.type == ToolType.MCP:
            server_label, tool_name = tool.name.split('--', maxsplit=1)
            user_approval = self.session.get_mcp_tool(server_label, tool_name).approval
        else:
            user_approval = self.session.get_opaca_tool_approval(tool.name)

        if any(x.lower() in tool.name.lower() for x in actions_blacklist):
            # First the admin blacklist is applied
            return ToolApprovalState.DENY
        if user_approval == ToolApprovalState.DENY:
            # Then the user's approval setting for the tool
            return ToolApprovalState.DENY
        if any(x.lower() in tool.name.lower() for x in actions_needing_confirmation):
            # Then the admin confirmation list
            return ToolApprovalState.ASK
        # Then either the users ask or allow
        return user_approval

    async def call_llm(
            self,
            model_config: LLMConfig,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[Literal["auto", "none", "only", "required"]] = "auto",
            response_format: Optional[Type[BaseModel]] = None,
            status_message: str | None = None,
            is_output: bool = False,
            attached_file_ids: set[str] | None = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
            model_config (Dict[str, Any]): Individual model configuration settings.
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt for model instructions.
            messages (List[ChatMessage]): The list of chat messages.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", "only", or "required").
            response_format (Optional[Type[BaseModel]]): Optional Pydantic schema to validate response.
            status_message (str): optional message to be streamed to the UI
            is_output (bool): whether agent output should be streamed directly to chat or only to debug
            attached_file_ids: IDs of files whose full contents should be attached to this call.
            By default, agents receive only a short file-availability notice.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """

        if status_message:
            await self.send_to_websocket(StatusMessage(agent=agent, status=status_message, chat_id=self.chat.chat_id))

        # Extract model name and config
        model = model_config.model

        # Check if an additional API key is required for this model
        if not self.session.get_api_key(model) and not litellm.validate_environment(model).get("keys_in_environment"):
            await self.handle_invalid_api_key(model)

        # Initialize variables
        exec_time = time.time()
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        file_message_parts = []
        if attached_file_ids:
            file_chat = Chat(chat_id=self.chat.chat_id, active_files=attached_file_ids)
            file_message_parts = await upload_files(self.session, file_chat, model)
            if not file_message_parts:
                file_list = ", ".join(
                    file.file_name
                    for file_id, file in self.session.uploaded_files.items()
                    if file_id in attached_file_ids
                ) or "the selected file"
                raise OpacaException(
                    user_message="The selected file could not be attached to the LLM.",
                    error_message=(
                        f"No supported file parts were produced for {file_list} using model {model}. "
                        "PDFs require a model provider with file-upload support; images require a "
                        "vision-capable OpenAI model in the current implementation."
                    ),
                )

        # Modify the last user message to include file parts
        if file_message_parts:
            last = messages[-1]

            # Normalize last content to "content parts"
            if isinstance(last.content, list):
                parts = last.content
            else:
                # assume string (or None)
                parts = [{"type": "input_text", "text": last.content or ""}]

            # Prepend file parts
            last.content = [*file_message_parts, *parts]

        if not attached_file_ids and self.internal_tools:
            current_file_ids = self.internal_tools.context.current_file_ids
            current_files = [
                f"{file.file_name} (ID: {file_id})"
                for file_id, file in self.session.uploaded_files.items()
                if file_id in current_file_ids
            ]
            if current_files:
                system_prompt = (
                    f"{system_prompt.rstrip()}\n\nFiles attached to this user message: "
                    f"{', '.join(current_files)}. References such as 'this file' or "
                    "'the attached file' mean these files. Use these IDs directly. For a "
                    "summary, overview, description, or main points, always call "
                    "GetFileSummaries first. Do not call AskFiles unless the stored summary is "
                    "unavailable or the user requests details beyond it. FindRelevantFiles is "
                    "unnecessary unless other uploaded files may also be relevant. "
                    "FindRelevantFiles searches all uploaded files and reports whether they are "
                    "active; if relevant files are inactive, call SetActiveFiles with the complete "
                    "relevant file set before GetFileSummaries or AskFiles."
                )
            elif self.session.uploaded_files:
                system_prompt = (
                    f"{system_prompt.rstrip()}\n\nUploaded files are available. Some may be "
                    "inactive for this chat. Use FindRelevantFiles when file selection is needed; "
                    "it searches all uploaded files using stored metadata and reports active "
                    "status. If relevant files are inactive, call SetActiveFiles with the complete "
                    "relevant file set before GetFileSummaries or AskFiles. For summaries, "
                    "overviews, descriptions, or main points, call GetFileSummaries before "
                    "AskFiles. AskFiles reads full contents and should only be used for details "
                    "that the stored summaries cannot provide."
                )

        # Set settings for model invocation
        kwargs = {
            'api_key': self.session.get_api_key(model),
            'model': model,
            'instructions': system_prompt,
            'input': [m.model_dump() for m in messages],
            'tools': tools or [],
            'tool_choice': tool_choice if tools else 'none',
            'text_format': response_format,
            'stream': True
        }

        # Add individual model configs and exclude unsupported/unset values
        kwargs |= model_config.parameters.model_dump(mode='json', exclude_unset=True)

        # If tool_choice is set to "only", use "auto" for external API call
        if tool_choice == "only":
            kwargs['tool_choice'] = 'auto'

        # Main stream logic
        stream = await litellm.aresponses(**kwargs)
        async for event in stream:

            # Abort the response generation for a specific chat,
            # or for all notifications and other anonymous queries at once.
            if (self.chat.is_aborted
                    or (self.chat.chat_id == '' and self.session.is_notifs_aborted)):
                raise OpacaException(
                    user_message="(The generation of the response has been stopped.)",
                    error_message="Completion generation aborted by user. See Debug/Logging Tab to see what has been done so far."
                )

            elif event.type == event_type.RESPONSE_FAILED:
                raise OpacaException(
                    user_message="(The generation of the response has failed. See error message for details.)",
                    error_message=f"{event.response.error['code']}: {event.response.error['message']}"
                )

            # Plain text chunk received
            elif event.type == event_type.OUTPUT_TEXT_DELTA:
                if tool_choice == "only":
                    break
                agent_message.content += event.delta
                await self.send_to_websocket(TextChunkMessage(id=agent_message.id, agent=agent, chunk=event.delta, is_output=is_output, chat_id=self.chat.chat_id))
                if event.delta and is_output:
                    self.response.content += event.delta

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
                        if t.name is None:
                            # Should not happen, exists just to get rid of pylance warnings
                            logger.warning("Received tool call without a name, skipping.")
                            continue

                        tool_type = self.determine_tool_type(t.name)

                        try:
                            tool = ToolCall(name=t.name, type=tool_type, id=self.next_tool_id(agent_message), args=json.loads(t.arguments))
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse tool arguments: {t.arguments}")
                            tool = ToolCall(name=t.name, type=tool_type, id=self.next_tool_id(agent_message), args={})
                        agent_message.tools.append(tool)
                        await self.send_to_websocket(ToolCallMessage(id=tool.id, name=tool.name, args=tool.args, agent=agent, chat_id=self.chat.chat_id))
                # Capture token usage
                agent_message.response_metadata = event.response.usage.model_dump()

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        await self.send_to_websocket(MetricsMessage(
            agent=agent,
            execution_time=agent_message.execution_time,
            metrics=agent_message.response_metadata,
            chat_id=self.chat.chat_id,
        ))

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message

    def determine_tool_type(self, tool_name: str) -> ToolType:
        """Determine tool type and name based on presence of server label and matching MCP server/tools"""
        provider = tool_name.split('--')[0]
        if self.internal_tools and self.internal_tools.is_internal_tool(provider):
            return ToolType.INTERNAL
        elif provider in self.session.mcp_servers:
            return ToolType.MCP
        else:
            return ToolType.OPACA

    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)

    async def invoke_all_tools(self, response: AgentMessage) -> List[ToolCall]:
        tasks = [self.invoke_tool(tool) for tool in response.tools]
        return await asyncio.gather(*tasks)

    async def invoke_tool(self, tool: ToolCall, login_attempt_retry: bool = False) -> ToolCall:
        """
        Invoke tool (OPACA or MCP) matching the given ToolCall.
        If OPACA invoke fails due to required login, attempt Login (via websocket callback) and try again.
        In any case returns a ToolCall, where "result" can be an error message.
        """
        async def create_result(result):
            await self.send_to_websocket(ToolResultMessage(id=tool.id, result=result, chat_id=self.chat.chat_id))
            return ToolCall(id=tool.id, type=tool.type, name=tool.name, args=tool.args, result=result)

        # If login_attempt_retry=True, the user has already been asked and allowed tool execution
        if not login_attempt_retry:
            approval_state = self._resolve_tool_approval(tool)

            if approval_state == ToolApprovalState.DENY:
                # Should not happen due to filtering in get_tools, but double-checking approval status just in case it changes in the future
                return await create_result("Execution denied by user settings, do not attempt again.")

            if approval_state == ToolApprovalState.ASK and not await self.check_confirmation(tool.name, tool.args):
                return await create_result("Execution declined by user, do not attempt again.")

        # tools are always formatted the same; provider can be MCP server or OPACA agent
        provider, tool_name = tool.name.split('--', maxsplit=1)

        # MCP Tool Execution Flow
        if tool.type == ToolType.MCP:
            server = self.session.mcp_servers.get(provider)
            try:
                client = MCPClient(server_url=server.server_url)
                res = await client.call_tool(CallToolRequestParams(name=tool_name, arguments=tool.args))
                if res.isError:
                    t_result = f"Execution failed. Error: {res.content}"
                else:
                    t_result = res.content
            except Exception as e:
                t_result = f"Failed to invoke MCP tool.\nCause: {e}"

        # Internal Tool Execution Flow
        elif tool.type == ToolType.INTERNAL:
            try:
                t_result = await self.internal_tools.call_internal_tool(tool_name, tool.args)
            except Exception as e:
                logger.exception("Internal tool %s failed", tool.name)
                cause = getattr(e, "error_message", None) or str(e) or type(e).__name__
                t_result = f"Failed to invoke Internal tool.\nCause: {cause}"

        # OPACA Tool Execution Flow
        else:
            try:
                t_result = await self.session.opaca_client.safe_invoke(tool_name, provider, tool.args)
            except httpx.HTTPStatusError as e:
                res = e.response.json()
                t_result = f"Failed to invoke OPACA tool.\nStatus code: {e.response.status_code}\nResponse: {e.response.text}\nResponse JSON: {res}"
                cause = res.get("cause", {}).get("message", "")
                status = res.get("cause", {}).get("statusCode", -1)
                if self.session.has_websocket() and (status in [401, 403] or ("401" in cause or "403" in cause or "credentials" in cause)):
                    return await self.handle_container_login(provider, tool_name, tool, login_attempt_retry)
            except Exception as e:
                t_result = f"Failed to invoke OPACA tool.\nCause: {e}"

        return await create_result(t_result)


    async def get_tools(self, include_internal: bool = True, include_mcp: bool = True, max_tools=128) -> tuple[list[dict], str]:
        """
        Get list of available actions as OpenAI Functions. This primarily includes the OPACA actions, but can also include "internal" tools.
        """
        tools, error = openapi_to_functions(await self.session.opaca_client.get_actions_openapi(inline_refs=True))

        if self.internal_tools and include_internal:
            tools.extend(self.internal_tools.get_internal_tools_openai())

        # Filter out OPACA tools if user denied OR if it hits the admin blacklist
        tools = [
            t for t in tools
            if self.session.get_opaca_tool_approval(t["name"]) != ToolApprovalState.DENY
            and not any(x.lower() in t["name"].lower() for x in actions_blacklist)
        ]

        # Gather, filter, and cast MCP tools (applying user settings and admin blacklist)
        if include_mcp and self.session.mcp_servers:
            mcp_tools = [
                tool.cast_to_openai_tool()
                for server in self.session.mcp_servers.values()
                for tool in server.tools.values()
                if tool.approval != ToolApprovalState.DENY
                and not any(x.lower() in tool.name.lower() for x in actions_blacklist)
            ]
            tools.extend(mcp_tools)

        if len(tools) > max_tools:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                    f"of {max_tools}. All tools after index {max_tools} will be ignored!\n")
            tools = tools[:max_tools]
        return tools, error


    async def check_confirmation(self, tool_name: str, parameters: dict) -> bool:
        """Use websocket to ask user for confirmation before executing the action.
        Returns whether the action may be executed or not.
        """
        if not self.session.has_websocket(): return False
        # ask user for confirmation, sharing lock-mechanism with container-login
        async with self.session.opaca_client.login_lock:
            await self.session.websocket_send(ConfirmActionNotification(tool=tool_name, params=parameters))
            return ConfirmActionResponse(**await self.session.websocket_receive()).allowed


    async def handle_container_login(self, agent_name: str, action_name: str, tool: ToolCall, login_attempt_retry: bool = False):
        """Handles failed tool invocation due to missing credentials."""

        # If a "missing credentials" error is encountered, initiate container login
        container_id, container_name = await self.session.opaca_client.get_most_likely_container_id(agent_name, action_name)

        # fix out-of-sync logged-in state, otherwise deadlock in retry within login-lock
        if container_id in self.session.opaca_client.container_tokens:
            del self.session.opaca_client.container_tokens[container_id]

        # This lock prevents more than one login-request message being sent to the UI at once. If multiple
        # invokes to actions of not-logged-in containers arrive, the second will wait here until the first
        # has been processed, and then immediately retry if it the same container, otherwise ask the user
        async with self.session.opaca_client.login_lock:
            # might already be logged in on lock-release if two actions of same container were called in parallel
            if container_id in self.session.opaca_client.container_tokens:
                return await self.invoke_tool(tool, True)
            while True:
                # Get credentials from user
                await self.session.websocket_send(ContainerLoginNotification(
                    container_name=container_name,
                    tool_name=tool.name,
                    retry=login_attempt_retry
                ))
                response = ContainerLoginResponse(**await self.session.websocket_receive())
                if not (response.username and response.password):
                    tool.result = "Failed to invoke tool.\nNo credentials provided."
                    return tool

                # Attempt to login at container via OPACA (error if immediate login-check fails)
                try:
                    await self.session.opaca_client.container_login(container_id, response.username, response.password)
                    break
                except Exception as e:
                    login_attempt_retry = True

        # login succeeded (or not checked by container) -> try to invoke the tool again
        res = await self.invoke_tool(tool, True)

        # Schedule a deferred logout based on the user-provided timeout
        asyncio.create_task(self.session.opaca_client.deferred_container_logout(container_id, response.timeout))

        return res

    async def handle_invalid_api_key(self, model, is_invalid: bool = False):
        if not self.session.has_websocket():
            raise OpacaException(user_message=f"No API key is available for model {model}.")
        await self.session.websocket_send(MissingApiKeyNotification(is_invalid=is_invalid, model=model))
        response = MissingApiKeyResponse(**await self.session.websocket_receive())
        if response.api_key:
            if litellm.check_valid_key(model, response.api_key):
                self.session.set_api_key(model, response.api_key)
            else:
                await self.handle_invalid_api_key(model, True)
        else:
            raise OpacaException(user_message=f"No valid API key was provided for model {model}!")

    def build_full_prompt(self, specific_prompt: str) -> str:
        """
        Provides a certain level of awareness of the LLM to (a) who it is, without repeating that
        in each prompt, as well as (b) things like the current date and time or the location.
        """
        SELF_INTRODUCTION_AND_CAPABILITIES = f"""
        You are part of an LLM Assistant called \"SAGE\". {self.get_time_and_location()} Following are your 
        individual tasks:
        """
        return "\n".join((SELF_INTRODUCTION_AND_CAPABILITIES, specific_prompt))

    @staticmethod
    def get_time_and_location():
        """dynamic prompt fragment including current date, time, and, if set, the location"""
        now = dt.strftime(dt.now(), "%B %d %Y, %H:%M")
        loc = os.getenv("LOCATION")
        if loc:
            return f"The current date and time is {now}. You are located at {loc}."
        else:
            return f"The current date and time is {now}."

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
