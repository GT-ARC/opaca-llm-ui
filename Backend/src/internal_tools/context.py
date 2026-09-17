from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..services.code_execution import CodeExecutor
from ..services.llm_calling import LLMCaller, get_internal_llm_config
from ..models import AgentMessage, ChatMessage, Chat, MetricsMessage, QueryResponse, SessionData

if TYPE_CHECKING:
    from ..strategies import AbstractMethod


@dataclass(slots=True)
class InternalToolContext:
    session: SessionData
    agent_method: type["AbstractMethod"]
    code_executor: CodeExecutor
    chat: Chat | None = None
    response: QueryResponse | None = None
    streaming: bool = False
    current_file_ids: set[str] = field(default_factory=set)

    async def record_agent_message(self, message: AgentMessage, agent_prefix: str | None = None) -> None:
        if self.response is None:
            return

        recorded_message = message.model_copy(deep=True)
        if agent_prefix:
            recorded_message.agent = f"{agent_prefix} / {recorded_message.agent}"
        self.response.agent_messages.append(recorded_message)

        if self.session.has_websocket() and self.streaming and self.chat:
            await self.session.websocket_send(MetricsMessage(
                agent=recorded_message.agent,
                execution_time=recorded_message.execution_time,
                metrics=recorded_message.response_metadata,
                chat_id=self.chat.chat_id,
            ))

    async def record_query_response(self, response: QueryResponse, agent_prefix: str | None = None) -> None:
        for message in response.agent_messages:
            await self.record_agent_message(message, agent_prefix)

    async def query(self, query: str, agent_prefix: str = "InternalTool") -> QueryResponse:
        """Call AgentMethod.query without streaming, chat history, or internal tools."""
        self.session.is_notifs_aborted = False
        response = QueryResponse(query=query)
        method_impl = self.agent_method(self.session, Chat(chat_id=''), response, streaming=False)
        result = await method_impl.query()
        await self.record_query_response(result, agent_prefix)
        return result

    async def call_llm(
            self, query: str, agent: str = "InternalTool",
            system_prompt: str = "You are a helpful assistant.",
    ) -> AgentMessage:
        """Make and record a single call without exposing tools or running a strategy."""
        caller = LLMCaller(
            session=self.session,
            chat=self.chat if self.chat is not None else Chat(chat_id=""),
            response=QueryResponse(query=query),
        )
        result = await caller.call_llm(
            model_config=get_internal_llm_config(self.session),
            agent=agent,
            system_prompt=system_prompt,
            messages=[ChatMessage(role="user", content=query)],
        )
        await self.record_agent_message(result)
        return result
