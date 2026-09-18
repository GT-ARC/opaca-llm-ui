from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Any, Type, Literal, Tuple
import asyncio
from datetime import datetime as dt
import os

from pydantic import BaseModel

from ..models import (ToolApprovalState, SessionData, QueryResponse, AgentMessage, ChatMessage, Chat,
                     ToolCall, MethodConfig, LLMConfig)
from ..services.opaca_client import actions_blacklist
from ..services.tool_calling import ToolCaller
from ..services.llm_calling import LLMCaller

if TYPE_CHECKING:
    from ..internal_tools import InternalTools


PLAY_BOOK_SYSTEM_NOTE = """
Play books are user-defined task instructions exposed through the LoadPlayBook internal tool.
If the current user request clearly matches one of the play books listed in that tool's description,
load the play book before answering or before choosing other tools. After LoadPlayBook returns, follow
the returned play book instructions for the rest of the current request while still respecting higher-priority
system rules. If a play book asks for exact final wording, output exactly that wording without adding a tool summary.
Do not load a play book if no listed play book is relevant.
"""


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
        self.internal_tools = internal_tools
        if self.internal_tools:
            self.internal_tools.set_chat(chat)
            self.internal_tools.set_response(response)
            self.internal_tools.set_streaming(streaming)
        self.tool_caller = ToolCaller(session, internal_tools, streaming, chat.chat_id)

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        return cls.CONFIG.model_json_schema(mode='serialization')

    def get_config(self) -> MethodConfig:
        return self.session.get_config(self)

    @abstractmethod
    async def query(self) -> QueryResponse:
        pass

    def next_tool_id(self, agent_message: AgentMessage):
        return self.tool_caller.next_tool_id(agent_message)

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
            model_config (LLMConfig): Individual model configuration settings.
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt for model instructions.
            messages (List[ChatMessage]): The list of chat messages.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", "only", or "required").
            response_format (Optional[Type[BaseModel]]): Optional Pydantic schema to validate response.
            status_message (str): optional message to be streamed to the UI
            is_output (bool): whether agent output should be streamed directly to chat or only to debug
            attached_file_ids: IDs of files whose full contents should be attached to this call; by default, agents receive only a list of recently added files.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """

        return await LLMCaller(
            session=self.session,
            chat=self.chat,
            response=self.response,
            streaming=self.streaming,
            internal_tools=self.internal_tools,
            tool_caller=self.tool_caller,
        ).call_llm(
            model_config=model_config, agent=agent, system_prompt=system_prompt,
            messages=messages, tools=tools, tool_choice=tool_choice,
            response_format=response_format, status_message=status_message,
            is_output=is_output, attached_file_ids=attached_file_ids,
        )

    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)

    async def invoke_all_tools(self, response: AgentMessage) -> List[ToolCall]:
        tasks = [self.invoke_tool(tool) for tool in response.tools]
        return await asyncio.gather(*tasks)

    async def invoke_tool(self, tool: ToolCall) -> ToolCall:
        return await self.tool_caller.invoke_tool(tool)

    async def get_tools(self, include_internal: bool = True, include_mcp: bool = True, max_tools=128) -> tuple[list[dict], str]:
        """
        Get list of available actions as OpenAI Functions. This primarily includes the OPACA actions, but can also include "internal" tools.
        """
        openapi_actions = await self.session.opaca_client.get_actions_openapi(inline_refs=False)
        tools, error = openapi_to_functions(openapi_actions)

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

    def build_full_prompt(self, specific_prompt: str) -> str:
        """
        Provides a certain level of awareness of the LLM to (a) who it is, without repeating that
        in each prompt, as well as (b) things like the current date and time or the location.
        """
        SELF_INTRODUCTION_AND_CAPABILITIES = f"""
        You are part of an LLM Assistant called \"SAGE\". {self.get_time_and_location()} Following are your 
        individual tasks:
        """
        prompt_parts = [SELF_INTRODUCTION_AND_CAPABILITIES]
        if self.session.enabled_play_books():
            prompt_parts.append(PLAY_BOOK_SYSTEM_NOTE)
        prompt_parts.append(specific_prompt)
        return "\n".join(prompt_parts)

    @staticmethod
    def get_time_and_location():
        """dynamic prompt fragment including current date, time, and, if set, the location"""
        now = dt.strftime(dt.now(), "%B %d %Y, %H:%M")
        loc = os.getenv("LOCATION")
        if loc:
            return f"The current date and time is {now}. You are located at {loc}."
        else:
            return f"The current date and time is {now}."


def openapi_to_functions(
        openapi_spec: dict,
        agent: str | None = None
) -> Tuple[List, str]:
    """
    Convert OpenAPI REST specification (with inlined references) to OpenAI Function specification.

    Parameters:
    - openapi_spec: the OpenAPI specification
    - agent: name of OPACA agent to filter for, or None for all
    """
    functions = []
    error_msg = ""
    component_schemas: dict = openapi_spec.get('components', {}).get('schemas', {})

    for path, methods in openapi_spec.get("paths", {}).items():
        for method, spec in methods.items():
            # Extract a name for the functions
            try:
                # The operation id is formatted as 'containerId;agentName;actionName'
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

            if schema is None:
                error_msg += f'No request body schema found for action {function_name}\n'
                continue

            try:
                schema = _make_inlined_schema(schema, component_schemas)
            except KeyError as e:
                error_msg += f'Unresolvable reference in action {function_name}: {e}\n'
                continue

            # must be present even if no params
            schema.setdefault("properties", {})

            functions.append({
                "type": "function",
                "name": agent_name + '--' + function_name,
                "description": desc,
                "parameters": schema,
            })

    return functions, error_msg


def _make_inlined_schema(schema: dict, component_schemas: dict) -> dict:
    """
    Inline the definitions of types used in the schema into the schema's $defs.

    This is needed since the tool schema passed to the LLM needs to be standalone
    and contain the definitions for all types referenced in it.

    :param schema: The tool schema where the definitions should be inlined.
    :param component_schemas: The full OAS components.

    :return: The schema with only the referenced sub-schemas inlined in $defs.
    """
    collected = {}
    rewritten = _rewrite_refs_and_collect_schemas(schema, component_schemas, collected)
    if collected:
        rewritten["$defs"] = collected
    return rewritten


def _rewrite_refs_and_collect_schemas(node: Any, component_schemas: dict, collected: dict) -> Any:
    """
    Replace components/schemas refs with $defs, and collect all
    schemas that were referenced at least once.
    """
    _COMPONENTS_PREFIX = "#/components/schemas/"
    _DEFS_PREFIX = "#/$defs/"

    if isinstance(node, dict):
        result = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith(_COMPONENTS_PREFIX):
                name = value[len(_COMPONENTS_PREFIX):]
                result[key] = _DEFS_PREFIX + name
                if name not in collected:
                    collected[name] = {}  # placeholder blocks re-entry on cycles
                    collected[name] = _rewrite_refs_and_collect_schemas(component_schemas[name], component_schemas, collected)
            else:
                result[key] = _rewrite_refs_and_collect_schemas(value, component_schemas, collected)
        return result

    if isinstance(node, list):
        return [_rewrite_refs_and_collect_schemas(item, component_schemas, collected) for item in node]

    return node
