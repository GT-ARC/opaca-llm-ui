from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..code_execution import CodeExecutor
from ..models import Chat, QueryResponse, SessionData

if TYPE_CHECKING:
    from ..abstract_method import AbstractMethod


@dataclass(slots=True)
class InternalToolContext:
    session: SessionData
    agent_method: type["AbstractMethod"]
    code_executor: CodeExecutor

    async def query(self, query: str) -> QueryResponse:
        """Call AgentMethod.query without streaming, chat history, or internal tools."""
        self.session.abort_sent = False
        return await self.agent_method(self.session, streaming=False).query(query, Chat(chat_id=""))

    def create_task_id(self) -> int:
        return max(self.session.scheduled_tasks, default=-1) + 1
