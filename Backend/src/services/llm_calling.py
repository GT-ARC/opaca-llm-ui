from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Type

import litellm
from litellm.types.llms.openai import ResponsesAPIStreamEvents as event_type
from pydantic import BaseModel, ValidationError

from ..models import (AgentMessage, Chat, ChatMessage, LLMConfig, QueryResponse,
                      SessionData, OpacaException, StatusMessage, TextChunkMessage,
                      MetricsMessage, MissingApiKeyNotification, MissingApiKeyResponse,
                      normalize_tool_schema_for_llm)
from .file_utils import get_file_parts
from .tool_calling import ToolCaller

if TYPE_CHECKING:
    from ..internal_tools import InternalTools

logger = logging.getLogger(__name__)


def get_internal_llm_config(session: SessionData) -> LLMConfig:
    """Use the existing simple-tools model preference for single-call internal tools."""
    config = session.config.get("simple-tools")
    if config is None:
        return LLMConfig()
    if not isinstance(config, dict):
        return config.model
    try:
        return LLMConfig.model_validate(config.get("model", {}))
    except ValidationError:
        logger.warning("Invalid internal LLM configuration; using the default model.")
        return LLMConfig()


class LLMCaller:
    """Issue one LLM response, without strategy selection or tool-execution loops."""

    def __init__(self, session: SessionData, chat: Chat, response: QueryResponse,
                 streaming: bool = False, internal_tools: InternalTools = None,
                 tool_caller: ToolCaller | None = None) -> None:
        self.session = session
        self.chat = chat
        self.response = response
        self.streaming = streaming
        self.internal_tools = internal_tools
        self.tool_caller = tool_caller or ToolCaller(session, internal_tools, streaming, chat.chat_id)

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

        system_prompt = await self._prepare_files(model, system_prompt, messages, tools, attached_file_ids)

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
                await self._handle_text_delta(event, agent_message, is_output)

            # Final message received
            elif event.type == event_type.RESPONSE_COMPLETED:
                await self._handle_completed(event, agent_message, response_format, model)

        agent_message.execution_time = time.time() - exec_time
        logger.debug(
            "LLM call finished id=%s agent=%s model=%s tool_calls=%d elapsed=%.3fs",
            agent_message.id, agent, model, len(agent_message.tools),
            agent_message.execution_time,
        )

        # Final stream to transmit execution time and response metadata
        await self.send_to_websocket(MetricsMessage(
            agent=agent,
            execution_time=agent_message.execution_time,
            metrics=agent_message.response_metadata,
            chat_id=self.chat.chat_id,
        ))

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message

    async def _prepare_files(
            self, model: str, system_prompt: str, messages: List[ChatMessage],
            tools: Optional[List[Dict[str, Any]]], attached_file_ids: set[str] | None,
    ) -> str:
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

        return system_prompt

    async def _handle_text_delta(self, event, agent_message: AgentMessage, is_output: bool) -> None:
        agent_message.content += event.delta
        await self.send_to_websocket(TextChunkMessage(id=agent_message.id, agent=agent_message.agent, chunk=event.delta, is_output=is_output, chat_id=self.chat.chat_id))
        if event.delta and is_output:
            self.response.content += event.delta

    async def _handle_completed(
            self, event, agent_message: AgentMessage,
            response_format: Optional[Type[BaseModel]], model: str,
    ) -> None:
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

        agent_message.tools.extend(await self.tool_caller.parse_tool_calls(
            event.response.output, agent_message
        ))
        # Capture token usage
        agent_message.response_metadata = event.response.usage.model_dump()

    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)

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
