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
from datetime import datetime, timedelta
from math import ceil

from pydantic import BaseModel
from typing import Callable
from textwrap import dedent

from .models import SessionData, Chat, PushMessage, ScheduledTask, QueryResponse


TIME_FORMAT = "%b %d %Y %H:%M"
INTERNAL_TOOLS_AGENT_NAME = "LLM-Assistant"

logger = logging.getLogger(__name__)


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    result: str
    function: Callable


class InternalTools:

    def __init__(self, session: SessionData, agent_method: type['AbstractMethod']):
        self.session = session
        self.agent_method = agent_method
        self.tools = [
            # TASK SCHEDULING
            InternalTool(
                name="ScheduleIntervalTask",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the interval in the query itself. Tasks can be executed just once or recurring. A negative value for 'repetitions' is interpreted as 'forever'. The delay should be a time in seconds for the first execution from now, and interval between executions, if applicable. Returns task ID",
                params={"query": "string", "delay_seconds": "integer", "repetitions": "integer"},
                result="integer",
                function=self.tool_schedule_task,
            ),
            InternalTool(
                name="ScheduleDailyTask",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the time in the query itself. Tasks can be executed just once or recurring. A negative value for 'repetitions' is interpreted as 'forever'. The task will be executed once per day at the specified time, in format 'HH:MM'. Returns task ID",
                params={"query": "string", "time_of_day": "string", "repetitions": "integer"},
                result="integer",
                function=self.tool_schedule_daily_task,
            ),
            InternalTool(
                name="GetScheduledTasks",
                description="Get list of scheduled tasks, including task IDs and details",
                params={},
                result="object",
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
        """get callback method for internal tool matching the name and call with given parameters"""
        callback = next(t.function for t in self.tools if t.name == tool)
        return await callback(**parameters)

    async def deferred_execution_helper(self, query: str, delay: int, interval: int, repetitions: int, task_id=None):
        """
        helper method used for creating different sorts of scheduled tasks (interval and daily)
        and for restoring serialized scheduled tasks after restart
        """
        async def _callback(wait_time: int, remaining: int):
            # wait until it's time to execute the task...
            await asyncio.sleep(wait_time)
            if task_id not in self.session.scheduled_tasks:
                logger.info(f"Scheduled task {task_id} has been cancelled")
                return

            # schedule next execution or remove task from list of tasks
            new_remaining = remaining - 1 if remaining > 0 else remaining
            if new_remaining != 0:
                asyncio.create_task(_callback(interval, new_remaining))
                self.session.scheduled_tasks[task_id] = make_task(interval, new_remaining)
            else:
                del self.session.scheduled_tasks[task_id]

            logger.info(f"Calling LLM for scheduled task {task_id}: {query}")

            # execute the task, then send result/error
            try:
                query_ext = dedent(f"""
                    This query was triggered by the 'ScheduleTask' tool: 

                    {query}

                    If it says to 'remind' the user of something, just output that thing the user asked about,
                    e.g. 'You asked me to remind you to ...'; do NOT create another 'ScheduleTask' reminder!
                    If it asked you to do something by that time, just do it and report on the results as usual.
                """)
                result = await self.query_method(query_ext)
            except Exception as e:
                logger.error(f"Scheduled task {task_id} failed:SCHEDULED TASK FAILED: {e}")
                result = QueryResponse.from_exception(query, e)
            await self.session.websocket_send(PushMessage(**result.model_dump()))

        def make_task(delay, remaining):
            next_time = (datetime.now() + timedelta(seconds=delay)).strftime(TIME_FORMAT)
            return ScheduledTask(method=self.agent_method.NAME, task_id=task_id, query=query, next_time=next_time, interval=interval, repetitions=remaining)

        if repetitions == 0:
            raise ValueError("Repetitions must not be zero")

        if task_id is None:
            task_id = self.create_task_id()
        self.session.scheduled_tasks[task_id] = make_task(delay, repetitions)
        asyncio.create_task(_callback(delay, repetitions))
        return task_id
    
    async def resume_scheduled_task(self, task: ScheduledTask):
        """resume scheduled task after deserialization"""
        now = datetime.now()
        then = datetime.strptime(task.next_time, TIME_FORMAT)
        skipped = 0
        if now >= then:
            skipped = ceil((now - then).seconds / task.interval)
            then += timedelta(seconds=task.interval) * skipped
            if task.repetitions >= 0:
                task.repetitions = max(0, task.repetitions - skipped)
        if task.repetitions != 0:
            logger.info(f"Resuming task {task.task_id} ({task.query}), after skipping {skipped} repetitions.")
            await self.deferred_execution_helper(task.query, (then - now).seconds, task.interval, task.repetitions, task.task_id)
        else:
            logger.info(f"Not resuming task {task.task_id} ({task.query}), all repetitions skipped.")
            del self.session.scheduled_tasks[task.task_id]

    async def query_method(self, query: str) -> QueryResponse:
        """short-hand for calling AgentMethod.query, without streaming, chat, or internal tools"""
        self.session.abort_sent = False
        return await self.agent_method(self.session, streaming=False).query(query, Chat(chat_id=''))

    def create_task_id(self) -> int:
        return max(self.session.scheduled_tasks, default=-1) + 1


    # IMPLEMENTATIONS OF ACTUAL TOOLS (see tool descriptions above for what those should do)

    async def tool_schedule_task(self, query: str, delay_seconds: int, repetitions: int) -> int:
        return await self.deferred_execution_helper(query, delay_seconds, delay_seconds, repetitions)

    async def tool_schedule_daily_task(self, query: str, time_of_day: str, repetitions: int) -> int:
        hh, mm = map(int, time_of_day.split(":"))
        now = datetime.now()
        sec_now = now.hour*3600 + now.minute*60 + now.second
        one_day = 24 * 60 * 60
        delay = ((60*hh + mm)*60 - sec_now) % one_day
        return await self.deferred_execution_helper(query, delay, one_day, repetitions)

    async def tool_get_scheduled_tasks(self) -> dict:
        return self.session.scheduled_tasks

    async def tool_cancel_scheduled_task(self, task_id: int) -> bool:
        if task_id in self.session.scheduled_tasks:
            del self.session.scheduled_tasks[task_id]
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
            res = await self.query_method(query)
            return res.content
        except Exception as e:
            return f"Search failed: {e}"

    async def tool_gather_user_infos(self) -> str:
        search_query = "Compile a short exposé about the current chat user, their personal situation, preferences, etc.."
        return await self.tool_search_chats(search_query)
    