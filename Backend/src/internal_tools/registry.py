from __future__ import annotations

from typing import TYPE_CHECKING

from ..code_execution import CodeExecutor
from ..models import ScheduledTask, SessionData
from .context import InternalToolContext
from .definitions import INTERNAL_TOOLS_AGENT_NAME, InternalTool

if TYPE_CHECKING:
    from ..abstract_method import AbstractMethod

class InternalTools:
    def __init__(self, session: SessionData, agent_method: type["AbstractMethod"]):
        from .chats import ChatTools
        from .code_tools import CodeTools
        from .files import FileTools
        from .scheduling import ScheduledTaskTools

        self.session = session
        self.agent_method = agent_method
        self.code_executor = CodeExecutor()
        self.context = InternalToolContext(
            session=self.session,
            agent_method=self.agent_method,
            code_executor=self.code_executor,
        )
        self.scheduling = ScheduledTaskTools(self.context)

        groups = [
            self.scheduling,
            ChatTools(self.context),
            FileTools(self.context),
            CodeTools(self.context),
        ]
        self.tools = [tool for group in groups for tool in group.tools()]

    def available_tools(self) -> list[InternalTool]:
        if CodeExecutor.available is True:
            return self.tools
        return [tool for tool in self.tools if not tool.requires_code_execution]

    def get_internal_tools_simple(self) -> dict[str, list[dict]]:
        """return internal tools in OPACA format used by simple agent"""
        return {
            INTERNAL_TOOLS_AGENT_NAME: [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        key: {
                            "type": val,
                            "required": key in (tool.required_params if tool.required_params is not None else tool.params.keys()),
                        }
                        for key, val in tool.params.items()
                    },
                    "result": {"type": tool.result, "required": True},
                }
                for tool in self.available_tools()
            ]
        }

    def get_internal_tools_openai(self) -> list[dict]:
        """return internal tools in OpenAI Functions format"""
        return [
            {
                "type": "function",
                "name": INTERNAL_TOOLS_AGENT_NAME + "--" + tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        key: {"type": val}
                        for key, val in tool.params.items()
                    },
                    "additionalProperties": False,
                    "required": tool.required_params if tool.required_params is not None else list(tool.params),
                },
            }
            for tool in self.available_tools()
        ]

    async def call_internal_tool(self, tool: str, parameters: dict):
        """get callback method for internal tool matching the name and call with given parameters"""
        tool_def = next((t for t in self.available_tools() if t.name == tool), None)
        if tool_def is None:
            raise ValueError(f"Internal tool '{tool}' is not available")
        return await tool_def.function(**parameters)

    async def resume_scheduled_task(self, task: ScheduledTask):
        """resume scheduled task after deserialization"""
        return await self.scheduling.resume_scheduled_task(task)

    async def query_method(self, query: str):
        """short-hand for calling AgentMethod.query, without streaming, chat, or internal tools"""
        return await self.context.query(query)

    def create_task_id(self) -> int:
        return self.context.create_task_id()
