from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List
import asyncio

import httpx
from litellm.experimental_mcp_client.client import MCPClient
from mcp.types import CallToolRequestParams
from pydantic import BaseModel

from ..models import (ToolApprovalState, SessionData,
                     ToolCall, ToolType, ContainerLoginNotification, ContainerLoginResponse,
                     ToolResultMessage, ConfirmActionNotification, ConfirmActionResponse)
from .opaca_client import actions_blacklist

if TYPE_CHECKING:
    from ..internal_tools import InternalTools


# list of string-fragments; if any action or agent name contains one of those, SAGE will ask for confirmation before calling the tool
actions_needing_confirmation: List[str] = []

logger = logging.getLogger(__name__)


class ToolCaller:

    def __init__(self, session: SessionData, internal_tools: InternalTools = None, streaming: bool = False, chat_id: str = "none") -> None:
        self.session = session
        self.internal_tools = internal_tools
        self.streaming = streaming
        self.chat_id = chat_id


    def determine_tool_type(self, tool_name: str) -> ToolType:
        """Determine tool type and name based on presence of server label and matching MCP server/tools"""
        provider = tool_name.split('--')[0]
        if self.internal_tools and self.internal_tools.is_internal_tool(provider):
            return ToolType.INTERNAL
        elif provider in self.session.mcp_servers:
            return ToolType.MCP
        else:
            return ToolType.OPACA


    async def invoke_tool(self, tool: ToolCall, login_attempt_retry: bool = False, skip_approval: bool = False) -> ToolCall:
        """
        Invoke tool (OPACA or MCP) matching the given ToolCall.
        If OPACA invoke fails due to required login, attempt Login (via websocket callback) and try again.
        In any case returns a ToolCall, where "result" can be an error message.
        """
        async def create_result(result):
            await self.send_to_websocket(ToolResultMessage(id=tool.id, result=result, chat_id=self.chat_id))
            return ToolCall(id=tool.id, type=tool.type, name=tool.name, args=tool.args, result=result)

        # If login_attempt_retry=True, the user has already been asked and allowed tool execution
        if not (login_attempt_retry or skip_approval):
            approval_state = self.resolve_tool_approval(tool)

            if approval_state == ToolApprovalState.DENY:
                # Should not happen due to filtering in get_tools, but double-checking approval status just in case it changes in the future
                return await create_result("Failed to invoke tool.\nExecution denied by user settings, do not attempt again.")

            if approval_state == ToolApprovalState.ASK and not await self.check_confirmation(tool.name, tool.args):
                return await create_result("Failed to invoke tool.\nExecution declined by user, do not attempt again.")

        # tools are always formatted the same; provider can be MCP server or OPACA agent
        provider, tool_name = tool.name.split('--', maxsplit=1)

        # MCP Tool Execution Flow
        if tool.type == ToolType.MCP:
            server = self.session.mcp_servers.get(provider)
            try:
                client = MCPClient(server_url=server.server_url)
                res = await client.call_tool(CallToolRequestParams(name=tool_name, arguments=tool.args))
                if res.isError:
                    t_result = f"Failed to invoke MCP tool.\nError: {res.content}"
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


    def resolve_tool_approval(self, tool: ToolCall) -> ToolApprovalState:
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


    async def check_confirmation(self, tool_name: str, parameters: dict) -> bool:
        """Use websocket to ask user for confirmation before executing the action.
        Returns whether the action may be executed or not.
        """
        if not self.session.has_websocket(): return False
        # ask user for confirmation, sharing lock-mechanism with container-login
        async with self.session.opaca_client.login_lock:
            msg_id = await self.session.websocket_send(ConfirmActionNotification(tool=tool_name, params=parameters))
            return ConfirmActionResponse(**await self.session.websocket_receive(msg_id)).allowed


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
                msg_id = await self.session.websocket_send(ContainerLoginNotification(
                    container_name=container_name,
                    tool_name=tool.name,
                    retry=login_attempt_retry
                ))
                response = ContainerLoginResponse(**await self.session.websocket_receive(msg_id))
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

    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)
