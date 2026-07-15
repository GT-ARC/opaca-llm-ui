from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..code_execution import CodeExecutor
from ..models import AgentMessage, Chat, MetricsMessage, QueryResponse, SessionData

if TYPE_CHECKING:
    from ..abstract_method import AbstractMethod


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
