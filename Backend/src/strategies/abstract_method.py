from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Any, Type, Literal, Tuple
import asyncio
from itertools import count
from datetime import datetime as dt
import os

from openai.types.responses import ResponseFunctionToolCall
from pydantic import BaseModel, ValidationError
import litellm
from litellm.types.responses.main import OutputFunctionToolCall
from litellm.types.llms.openai import ResponsesAPIStreamEvents as event_type

from ..models import (ToolApprovalState, SessionData, QueryResponse, AgentMessage, ChatMessage, OpacaException, Chat,
                     ToolCall, ToolCallMessage, TextChunkMessage, MetricsMessage, StatusMessage, MethodConfig,
                     MissingApiKeyNotification, MissingApiKeyResponse, LLMConfig, normalize_tool_schema_for_llm)
from ..services.file_utils import get_file_parts
from ..services.opaca_client import actions_blacklist
from ..services.tool_calling import ToolCaller

if TYPE_CHECKING:
    from ..internal_tools import InternalTools


logger = logging.getLogger(__name__)

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
        self.tool_counter = count(0)
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
        return f"{agent_message.id}/{next(self.tool_counter)}"

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
            attached_file_ids: IDs of files whose full contents should be attached to this call; by default, agents receive only a list of recently added files.

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

        # Full file contents are opt-in per LLM call. Only these explicitly requested
        # files are uploaded to the provider and added to the model input.
        if attached_file_ids:
            file_message_parts = await get_file_parts(self.session, model, attached_file_ids)

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
            last = messages[-1]

            # Normalize last content to "content parts"
            if isinstance(last.content, list):
                parts = last.content
            else:
                # assume string (or None)
                parts = [{"type": "input_text", "text": last.content or ""}]

            # Prepend file parts
            last.content = [*file_message_parts, *parts]

        # Without full contents, preserve only which files belong to the current user request.
        # This lets the model resolve references such as "this file" without sending their contents.
        # current_file_ids originates from QueryRequest.
        if not attached_file_ids and self.internal_tools and tools:
            current_file_ids = self.internal_tools.context.current_file_ids
            current_files = [
                f"{file.file_name} (ID: {file_id})"
                for file_id, file in self.session.uploaded_files.items()
                if file_id in current_file_ids
            ]
            if current_files:
                system_prompt = (
                    f"{system_prompt.rstrip()}\n\nFiles attached to this request: "
                    f"{', '.join(current_files)}."
                )

        # Set settings for model invocation
        kwargs = {
            'api_key': self.session.get_api_key(model),
            'model': model,
            'instructions': system_prompt,
            'input': [m.model_dump() for m in messages],
            # Normalize all tool sources at their common LLM boundary while
            # preserving the original schemas used by their providers.
            'tools': normalize_tool_schema_for_llm(tools or []),
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

                        tool_type = self.tool_caller.determine_tool_type(t.name)

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

    async def handle_invalid_api_key(self, model, is_invalid: bool = False):
        if not self.session.has_websocket():
            msg = f"The API key for {model} is invalid." if is_invalid else f"No API key is available for {model}."
            raise OpacaException(user_message=msg)
        msg_id = await self.session.websocket_send(MissingApiKeyNotification(is_invalid=is_invalid, model=model))
        response = MissingApiKeyResponse(**await self.session.websocket_receive(msg_id))
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
