"""
Wrapper for different internal tools, to be provided to the OPACA LLM as "actions" like OPACA,
but implemented directly in the backend.

Those tools are then added to the OPACA Proxy's actions in the AbstracMethod's get_tools method.
The AbstractMethod's invoke_tool method then checks if the tools belong to the "internal" agent.

Some of the tools (like execute-later or maybe summarize-file) may again issue LLM calls.
For this they have access to the AbstractMethod they are used by.
"""

import asyncio
import logging
import json
from itertools import count

from pydantic import BaseModel
from typing import Callable
from textwrap import dedent

from .models import SessionData, Chat, PendingCallback, PushMessage


INTERNAL_TOOLS_AGENT_NAME = "LLM-Assistant"

logger = logging.getLogger(__name__)


# TODO this is here only temporarily... it should probably also be a part of SessionData, 
# so that each user has different scheduled tasks.
# but then, should it also be persisted to DB? this would mean restoring the scheduled tasks
# afterwards (including updated next execution), which might again be tricky since they are also
# linked to the abstract-method they were created in...
SCHEDULED_TASKS = {}
task_ids_provider = count()


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    result: str
    function: Callable


class InternalTools:

    def __init__(self, session: SessionData, agent_method: 'AbstractMethod'):
        self.session = session
        self.agent_method = agent_method
        self.tools = [
            # TASK SCHEDULING
            InternalTool(
                name="ScheduleTask",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Tasks can be executed just once or recurring. The interval should be a time in seconds for the first execution from now, and interval between executions, if applicable. Returns task ID",
                params={"query": "string", "delay_seconds": "integer", "recurring": "boolean"},
                result="integer",
                function=self.tool_schedule_task,
            ),
            InternalTool(
                name="GetScheduledTasks",
                description="Get list of scheduled tasks, including task IDs and details",
                params={},
                result="integer",
                function=self.tool_get_scheduled_tasks,
            ),
            InternalTool(
                name="CancelScheduleTask",
                description="Cancel a previously scheduled task. Return true/false whether a task with this ID existed.",
                params={"task_id": "integer"},
                result="boolean",
                function=self.tool_cancel_scheduled_task,
            ),
            # INTROSPECTION
            InternalTool(
                name="GatherUserInfo",
                description="Compiles a short expose about the current chat user from this and past interactions, their personal situation, preferences, etc..",
                params={},
                result="string",
                function=self.tool_gather_user_infos,
            ),
            InternalTool(
                name="SearchChats",
                description="Search this and past interactions about information on the given topic and summarize the findings.",
                params={"search_query": "string"},
                result="string",
                function=self.tool_search_chats,
            ),
        ]

    def get_internal_tools_simple(self) -> dict[str, list[dict]]:
        """return internal tools in OPACA format used by simple agent"""
        return {
            INTERNAL_TOOLS_AGENT_NAME: [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        key: {"type": val, "required": True}
                        for key, val in tool.params.items()
                    },
                    "result": {"type": tool.result, "required": True}
                }
                for tool in self.tools
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
                    "required": list(tool.params),
                }
            }
            for tool in self.tools
        ]

    async def call_internal_tool(self, tool: str, parameters: dict):
        callback = next(t.function for t in self.tools if t.name == tool)
        return await callback(**parameters)


    # IMPLEMENTATIONS OF ACTUAL TOOLS

    async def tool_schedule_task(self, query: str, delay_seconds: int, recurring: bool) -> int:
        task_id = next(task_ids_provider)

        async def _callback():
            logger.info("WAITING...")
            await asyncio.sleep(delay_seconds)
            if task_id not in SCHEDULED_TASKS:
                logger.info("SCHEDULE TASK WAS CANCELLED")
                return

            logger.info("CALLING LLM NOW...")
            try:
                await self.session.websocket_send(PendingCallback(query=query))

                query_extra = "\n\nNOTE: This query was triggered by the 'execute-later' tool. If it says to 'remind' the user of something, just output that thing the user asked about, e.g. 'You asked me to remind you to ...'; do NOT create another 'execute-later' reminder! If it just asked you to do something by that time, just do it and report on the results as usual."
                res = await self.agent_method.query(query + query_extra, Chat(chat_id=''))
                logger.info(f"SCHEDULED TASK RESULT: {res.content}")

                await self.session.websocket_send(PushMessage(**res.model_dump()))

            except Exception as e:
                logger.error(f"SCHEDULED TASK FAILED: {e}")
                # TODO send error

            if recurring:
                asyncio.create_task(_callback())
            elif task_id in SCHEDULED_TASKS:
                del SCHEDULED_TASKS[task_id]

        asyncio.create_task(_callback())
        SCHEDULED_TASKS[task_id] = {"task_id": task_id, "query": query, "interval": delay_seconds, "recurring": recurring}
        return task_id
    
    async def tool_get_scheduled_tasks(self) -> dict:
        return SCHEDULED_TASKS

    async def tool_cancel_scheduled_task(self, task_id: int) -> bool:
        if task_id in SCHEDULED_TASKS:
            del SCHEDULED_TASKS[task_id]
            return True
        return False

    async def tool_search_chats(self, search_query: str) -> str:
        messages = [[f"{m.role}: {m.content}" for m in chat.messages] for chat in self.session.chats.values()]
        query = dedent(f"""
        In the following is the full transcript of all past interactions between the User and the LLM Assistant:
        
        {json.dumps(messages, indent=2)}

        Use this transcript to answer the following query:

        {search_query}
        """)
        try:
            res = await self.agent_method.query(query, Chat(chat_id=''))
            return res.content
        except Exception as e:
            return f"Search failed: {e}"

    async def tool_gather_user_infos(self) -> str:
        search_query = "Compile a short expose about the current chat user, their personal situation, preferences, etc.."
        return await self.tool_search_chats(search_query)
    