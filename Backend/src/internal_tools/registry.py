"""
Wrapper for different internal tools, to be provided to the OPACA LLM as "actions" like OPACA,
but implemented directly in the backend.

Those tools are then added to the OPACA Proxy's actions in the AbstractMethod's get_tools method.
The AbstractMethod's invoke_tool method then checks if the tools belong to the "internal" agent.

Some of the tools (like execute-later or summarize-chat) may again issue LLM calls.
For this they have access to the AbstractMethod they are used by.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..code_execution import CodeExecutor
from ..models import InternalTool, ScheduledTask, SessionData
from .context import InternalToolContext
from .chats import ChatTools
from .code_tools import CodeTools
from .files import FileTools
from .scheduling import ScheduledTaskTools

if TYPE_CHECKING:
    from ..abstract_method import AbstractMethod


ToolGroup = ScheduledTaskTools | ChatTools | FileTools | CodeTools
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

    def set_chat(self, chat):
        self.context.chat = chat

    def set_current_file_ids(self, file_ids: set[str]):
        self.context.current_file_ids = file_ids

    # FORMAT INTERNAL TOOLS FOR DIFFERENT OCCASIONS

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
    
    def _format_internal_tool_group_simple(self, group: ToolGroup) -> list[dict]:
        return [self._format_internal_tool_simple(tool) for tool in group.tools()]

    def get_internal_tools_simple(self) -> dict[str, list[dict]]:
        """return internal tools in simplified OPACA format used by simple agent"""
        return {
            group.GROUP_NAME: self._format_internal_tool_group_simple(group)
            for group in self.groups if group.tools()
        }

    def get_internal_tools_containers(self) -> list[dict]:
        """return internal tools as a pseudo OPACA container for UI display"""
        agents = [
            {
                "agentId": group.GROUP_NAME,
                "actions": self._format_internal_tool_group_simple(group),
            }
            for group in self.groups if group.tools()
        ]
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
                "name": group.GROUP_NAME + "--" + tool.name,
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
            for group in self.groups
            for tool in group.tools()
        ]

    # EXECUTING INTERNAL TOOLS, delegating to the respective tool group

    def is_internal_tool(self, provider: str) -> bool:
        return any(group.GROUP_NAME == provider for group in self.groups)

    async def call_internal_tool(self, tool: str, parameters: dict):
        """get callback method for internal tool matching the name and call with given parameters"""
        tool_def = next((t for g in self.groups for t in g.tools() if t.name == tool), None)
        if tool_def is None:
            raise ValueError(f"Internal tool '{tool}' is not available")
        return await tool_def.function(**parameters)

    async def resume_scheduled_task(self, task: ScheduledTask):
        """resume scheduled task after deserialization"""
        task_scheduler = next(group for group in self.groups if isinstance(group, ScheduledTaskTools))
        return await task_scheduler.resume_scheduled_task(task)
