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
import requests
from datetime import datetime, timedelta
from math import ceil

from pydantic import BaseModel
from typing import Any, Callable
from textwrap import dedent

from .file_utils import register_bytes_as_uploaded_file, filename_from_url_and_type
from .models import SessionData, Chat, PushAdvert, PushMessage, ScheduledTask, QueryResponse


TIME_FORMAT = "%b %d %Y %H:%M"
INTERNAL_TOOLS_AGENT_NAME = "LLM-Assistant"
WEEKDAYS_SCHEMA = {
    "type": "array",
    "items": {"type": "integer"},
    "description": "Weekdays using 0=Monday, 1=Tuesday, ..., 6=Sunday.",
}

logger = logging.getLogger(__name__)


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str | dict[str, Any]]
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
                name="ScheduleWeeklyTask",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the time or weekdays in the query itself. Tasks can be executed just once or recurring. A negative value for 'repetitions' is interpreted as 'forever'. The task will be executed at the specified time, in format 'HH:MM', on the specified weekdays. 'weekdays' uses 0=Monday, 1=Tuesday, ..., 6=Sunday. Returns task ID",
                params={"query": "string", "time_of_day": "string", "weekdays": WEEKDAYS_SCHEMA, "repetitions": "integer"},
                result="integer",
                function=self.tool_schedule_weekly_task,
            ),
            InternalTool(
                name="ScheduleWindowedIntervalTask",
                description="Schedule a recurring bounded time window in which the query should run repeatedly. At the specified start time on the specified weekdays, a finite interval schedule will be started internally. Use this only when the request gives a clear start time and window duration/end time. Use 'start_time' in format 'HH:MM'. 'weekdays' uses 0=Monday, 1=Tuesday, ..., 6=Sunday. Use 'interval_seconds' for the repeat interval inside the window, and 'duration_seconds' for the total window length starting at 'start_time'. 'repetitions' counts how many such windows should be started; a negative value means forever. Returns task ID",
                params={"query": "string", "start_time": "string", "weekdays": WEEKDAYS_SCHEMA, "interval_seconds": "integer", "duration_seconds": "integer", "repetitions": "integer"},
                result="integer",
                function=self.tool_schedule_windowed_interval_task,
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
            InternalTool(
                name="ReadFileFromUrl",
                description="Downloads a file from a URL and uploads it to the backend to be used by the LLM.",
                params={"url": "string"},
                result="object",
                function=self.tool_read_file_from_url,
            )
        ]

    def _param_schema(self, schema: str | dict[str, Any]) -> dict:
        return {"type": schema} if isinstance(schema, str) else schema

    def get_internal_tools_simple(self) -> dict[str, list[dict]]:
        """return internal tools in OPACA format used by simple agent"""
        return {
            INTERNAL_TOOLS_AGENT_NAME: [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        key: {**self._param_schema(val), "required": True}
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
                        key: self._param_schema(val)
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

    def _get_next_calendar_time(self, current: datetime, time_of_day: str, weekdays: list[int]) -> datetime:
        hh, mm = map(int, time_of_day.split(":"))
        for days_ahead in range(8):
            candidate = current + timedelta(days=days_ahead)
            candidate = candidate.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if candidate.weekday() in weekdays and candidate > current:
                return candidate
        raise ValueError("Could not compute next execution time")

    def _get_next_delay(self, current: datetime, interval: int, time_of_day: str | None = None, weekdays: list[int] | None = None) -> int:
        if time_of_day is None or weekdays is None:
            return interval
        next_time = self._get_next_calendar_time(current, time_of_day, weekdays)
        return ceil((next_time - current).total_seconds())

    async def deferred_execution_helper(
        self,
        query: str,
        delay: int,
        interval: int,
        repetitions: int,
        task_id=None,
        time_of_day: str | None = None,
        weekdays: list[int] | None = None,
        parent_task_id: int | None = None,
        spawn_interval_seconds: int | None = None,
        spawn_repetitions: int | None = None,
    ):
        """
        helper method used for creating different sorts of scheduled tasks (interval and daily/weekly)
        and for restoring serialized scheduled tasks after restart
        """
        async def _callback(wait_time: int, remaining: int):
            # wait until it's time to execute the task...
            await asyncio.sleep(wait_time)
            if task_id not in self.session.scheduled_tasks:
                logger.info(f"Scheduled task {task_id} has been cancelled")
                return
            task = self.session.scheduled_tasks[task_id]

            # schedule next execution or remove task from list of tasks
            new_remaining = remaining - 1 if remaining > 0 else remaining
            if new_remaining != 0:
                next_delay = self._get_next_delay(datetime.now(), interval, time_of_day, weekdays)
                asyncio.create_task(_callback(next_delay, new_remaining))
                self.session.scheduled_tasks[task_id] = make_task(next_delay, new_remaining)
            else:
                del self.session.scheduled_tasks[task_id]

            if task.spawn_interval_seconds is not None and task.spawn_repetitions is not None:
                await self.deferred_execution_helper(
                    query=task.query,
                    delay=0,
                    interval=task.spawn_interval_seconds,
                    repetitions=task.spawn_repetitions,
                    parent_task_id=task.task_id,
                )
                return

            logger.info(f"Calling LLM for scheduled task {task_id}: {query}")

            # execute the task, then send result/error
            await self.session.websocket_send(PushAdvert(task_id=task_id, query=query))
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

            # Clean mapping
            self.session.prune_notifications_chats_map()

            push_message = PushMessage(task_id=task_id, **result.model_dump())

            # Append to all chats that are selected for auto-append
            for chat_id in self.session.notifications_chats_map.get(task_id, []):
                chat = self.session.get_or_create_chat(chat_id)
                message_copy = push_message.model_copy(deep=True)
                message_copy.query = ""
                chat.store_interaction(message_copy)

            await self.session.websocket_send(push_message)

        def make_task(next_delay, remaining):
            next_time = (datetime.now() + timedelta(seconds=next_delay)).strftime(TIME_FORMAT)
            stored_interval = interval if time_of_day is None or weekdays is None else next_delay
            return ScheduledTask(
                method=self.agent_method.NAME,
                task_id=task_id,
                query=query,
                next_time=next_time,
                interval=stored_interval,
                time_of_day=time_of_day,
                weekdays=weekdays,
                parent_task_id=parent_task_id,
                spawn_interval_seconds=spawn_interval_seconds,
                spawn_repetitions=spawn_repetitions,
                repetitions=remaining,
            )

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
        if task.weekdays is None or task.time_of_day is None:
            if now >= then:
                skipped = ceil((now - then).total_seconds() / task.interval)
                then += timedelta(seconds=task.interval) * skipped
                if task.repetitions >= 0:
                    task.repetitions = max(0, task.repetitions - skipped)
        else:
            while task.repetitions != 0 and now >= then:
                skipped += 1
                if task.repetitions > 0:
                    task.repetitions -= 1
                if task.repetitions != 0:
                    then = self._get_next_calendar_time(then, task.time_of_day, task.weekdays)
        if task.repetitions != 0:
            logger.info(f"Resuming task {task.task_id} ({task.query}), after skipping {skipped} repetitions.")
            await self.deferred_execution_helper(
                task.query,
                max(0, ceil((then - now).total_seconds())),
                task.interval,
                task.repetitions,
                task.task_id,
                task.time_of_day,
                task.weekdays,
                task.parent_task_id,
                task.spawn_interval_seconds,
                task.spawn_repetitions,
            )
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
        delay = self._get_next_delay(datetime.now(), 24 * 60 * 60, time_of_day, list(range(7)))
        return await self.deferred_execution_helper(
            query,
            delay,
            24 * 60 * 60,
            repetitions,
            time_of_day=time_of_day,
            weekdays=list(range(7)),
        )

    async def tool_schedule_weekly_task(self, query: str, time_of_day: str, weekdays: list[int], repetitions: int) -> int:
        delay = self._get_next_delay(datetime.now(), 7 * 24 * 60 * 60, time_of_day, weekdays)
        return await self.deferred_execution_helper(
            query,
            delay,
            7 * 24 * 60 * 60,
            repetitions,
            time_of_day=time_of_day,
            weekdays=weekdays,
        )

    async def tool_schedule_windowed_interval_task(
        self,
        query: str,
        start_time: str,
        weekdays: list[int],
        interval_seconds: int,
        duration_seconds: int,
        repetitions: int,
    ) -> int:

        delay = self._get_next_delay(datetime.now(), 7 * 24 * 60 * 60, start_time, weekdays)
        return await self.deferred_execution_helper(
            query=query,
            delay=delay,
            interval=7 * 24 * 60 * 60,
            repetitions=repetitions,
            time_of_day=start_time,
            weekdays=weekdays,
            spawn_interval_seconds=interval_seconds,
            spawn_repetitions=duration_seconds // interval_seconds + 1,
        )

    async def tool_get_scheduled_tasks(self) -> dict:
        return self.session.scheduled_tasks

    async def tool_cancel_scheduled_task(self, task_id: int) -> bool:
        task_ids = {task_id}
        changed = True
        while changed:
            changed = False
            for current_id, task in list(self.session.scheduled_tasks.items()):
                if task.parent_task_id in task_ids and current_id not in task_ids:
                    task_ids.add(current_id)
                    changed = True
        existed = any(current_id in self.session.scheduled_tasks for current_id in task_ids)
        for current_id in task_ids:
            self.session.scheduled_tasks.pop(current_id, None)
        return existed

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

    async def tool_read_file_from_url(self, url: str) -> dict:
        try:
            resp = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type")
            filename = filename_from_url_and_type(url, content_type)

            await register_bytes_as_uploaded_file(
                session=self.session,
                content_type=content_type,
                filename=filename,
                data=resp.content,
            )

            return {
                "ok": True,
                "filename": filename,
                "note": "File downloaded and made available for analysis.",
            }

        except Exception as e:
            logger.error(str(e))
            return {
                "ok": False,
                "error": str(e),
            }
