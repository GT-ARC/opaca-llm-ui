from __future__ import annotations

from typing import TYPE_CHECKING

from ..code_execution import CodeExecutor
from ..models import ScheduledTask, SessionData
from .context import InternalToolContext
from .definitions import INTERNAL_TOOLS_AGENT_NAME, InternalTool
from .chats import ChatTools
from .code_tools import CodeTools
from .files import FileTools
from .scheduling import ScheduledTaskTools

if TYPE_CHECKING:
    from ..abstract_method import AbstractMethod


TOOL_GROUPS = (
    ScheduledTaskTools,
    ChatTools,
    FileTools,
    CodeTools,
)


class InternalTools:
    def __init__(self, session: SessionData, agent_method: type["AbstractMethod"]):
        self.session = session
        self.agent_method = agent_method
        self.code_executor = CodeExecutor()
        self.context = InternalToolContext(
            session=self.session,
            agent_method=self.agent_method,
            code_executor=self.code_executor,
        )
        self.groups = [group_cls(self.context) for group_cls in TOOL_GROUPS]
        self.group_tools = [(group, group.tools()) for group in self.groups]
        self.tools = [tool for _, tools in self.group_tools for tool in tools]

    def _get_group(self, group_type):
        return next(group for group in self.groups if isinstance(group, group_type))

    def available_tools(self) -> list[InternalTool]:
        if CodeExecutor.available is True:
            return self.tools
        return [tool for tool in self.tools if not tool.requires_code_execution]

    def _format_internal_tool_simple(self, tool: InternalTool) -> dict:
        return {
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

    def get_internal_tools_simple(self) -> dict[str, list[dict]]:
        """return internal tools in OPACA format used by simple agent"""
        return {
            INTERNAL_TOOLS_AGENT_NAME: [
                self._format_internal_tool_simple(tool)
                for tool in self.available_tools()
            ]
        }

    def get_internal_tools_containers(self) -> list[dict]:
        """return internal tools as a pseudo OPACA container for UI display"""
        agents = []
        for group, tools in self.group_tools:
            actions = [
                self._format_internal_tool_simple(tool)
                for tool in tools
                if CodeExecutor.available is True or not tool.requires_code_execution
            ]
            if actions:
                agents.append({
                    "agentId": group.GROUP_NAME,
                    "actions": actions,
                })

        return [{
            "containerId": "__internal_tools__",
            "image": {
                "imageName": "Internal Tools",
                "name": "Internal Tools",
                "version": "builtin",
                "provider": "SAGE",
            },
            "agents": agents,
        }]

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
        return await self._get_group(ScheduledTaskTools).resume_scheduled_task(task)

    async def query_method(self, query: str):
        """short-hand for calling AgentMethod.query, without streaming, chat, or internal tools"""
        return await self.context.query(query)
