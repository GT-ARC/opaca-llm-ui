from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from math import ceil
from textwrap import dedent

from ..models import InternalTool, PushAdvert, PushMessage, QueryResponse, ScheduledTask
from .context import InternalToolContext


TIME_FORMAT = "%b %d %Y %H:%M"
DAYS_OF_WEEK = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

logger = logging.getLogger(__name__)


class ScheduledTaskTools:
    GROUP_NAME = "Scheduled Tasks"

    def __init__(self, ctx: InternalToolContext):
        self.ctx = ctx

    def tools(self) -> list[InternalTool]:
        return [
            InternalTool(
                name="ScheduleIntervalTask",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the interval in the query itself. Tasks can be executed just once or recurring. A negative value for 'repetitions' is interpreted as 'forever'. The delay should be a time in seconds for the first execution from now, and interval between executions, if applicable. Returns task ID",
                params={"query": "string", "delay_seconds": "integer", "repetitions": "integer"},
                result="integer",
                function=self.tool_schedule_interval_task,
            ),
            InternalTool(
                name="ScheduleCalendarTask",
                description="Schedule some action to be executed forever on a calendar schedule. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the time or weekdays in the query itself. The task repeats forever. 'weekdays' must be a comma-separated list like 'Mon,Fri'; Pass an empty string for 'weekdays' to make it a daily task. For 'time_of_day' pass the local time in format 'HH:MM', or an empty string to use the current local time. Returns task ID",
                params={"query": "string", "time_of_day": "string", "weekdays": "string"},
                result="integer",
                function=self.tool_schedule_calendar_task,
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
        ]

    def _parse_weekdays(self, weekdays: str) -> list[int]:
        return [DAYS_OF_WEEK.index(day.strip().lower()[:3]) for day in weekdays.split(",")]

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

    def create_task_id(self) -> int:
        return max(self.ctx.session.scheduled_tasks, default=-1) + 1

    async def deferred_execution_helper(
        self,
        query: str,
        delay: int,
        interval: int,
        repetitions: int,
        task_id=None,
        time_of_day: str | None = None,
        weekdays: list[int] | None = None,
    ):
        """
        helper method used for creating different sorts of scheduled tasks (interval and daily/weekly)
        and for restoring serialized scheduled tasks after restart
        """
        session = self.ctx.session

        async def _callback(wait_time: int, remaining: int):
            # wait until it's time to execute the task...
            await asyncio.sleep(wait_time)
            if task_id not in session.scheduled_tasks:
                logger.info(f"Scheduled task {task_id} has been cancelled")
                return

            # schedule next execution or remove task from list of tasks
            new_remaining = remaining - 1 if remaining > 0 else remaining
            if new_remaining != 0:
                next_delay = self._get_next_delay(datetime.now(), interval, time_of_day, weekdays)
                asyncio.create_task(_callback(next_delay, new_remaining))
                session.scheduled_tasks[task_id] = make_task(next_delay, new_remaining)
            else:
                del session.scheduled_tasks[task_id]

            logger.info(f"Calling LLM for scheduled task {task_id}: {query}")

            # execute the task, then send result/error
            await session.websocket_send(PushAdvert(task_id=task_id, query=query))
            try:
                query_ext = dedent(f"""
                    This query was triggered by the 'ScheduleTask' tool: 

                    {query}

                    If it says to 'remind' the user of something, just output that thing the user asked about,
                    e.g. 'You asked me to remind you to ...'; do NOT create another 'ScheduleTask' reminder!
                    If it asked you to do something by that time, just do it and report on the results as usual.
                """)
                result = await self.ctx.query(query_ext)
            except Exception as e:
                logger.error(f"Scheduled task {task_id} failed:SCHEDULED TASK FAILED: {e}")
                result = QueryResponse.from_exception(query, e)

            # Clean mapping
            session.prune_notifications_chats_map()

            push_message = PushMessage(task_id=task_id, **result.model_dump())

            # Append to all chats that are selected for auto-append
            for chat_id in session.notifications_chats_map.get(task_id, []):
                chat = session.get_or_create_chat(chat_id)
                message_copy = push_message.model_copy(deep=True)
                message_copy.query = ""
                chat.store_interaction(message_copy)

            await session.websocket_send(push_message)

        def make_task(next_delay, remaining):
            next_time = (datetime.now() + timedelta(seconds=next_delay)).strftime(TIME_FORMAT)
            stored_interval = interval if time_of_day is None or weekdays is None else next_delay
            return ScheduledTask(
                method=self.ctx.agent_method.NAME,
                task_id=task_id,
                query=query,
                next_time=next_time,
                interval=stored_interval,
                time_of_day=time_of_day,
                weekdays=weekdays,
                repetitions=remaining,
            )

        if repetitions == 0:
            raise ValueError("Repetitions must not be zero")

        if task_id is None:
            task_id = self.create_task_id()
        session.scheduled_tasks[task_id] = make_task(delay, repetitions)
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
            while now >= then:
                skipped += 1
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
            )
        else:
            logger.info(f"Not resuming task {task.task_id} ({task.query}), all repetitions skipped.")
            del self.ctx.session.scheduled_tasks[task.task_id]

    async def tool_schedule_interval_task(self, query: str, delay_seconds: int, repetitions: int) -> int:
        return await self.deferred_execution_helper(query, delay_seconds, delay_seconds, repetitions)

    async def tool_schedule_calendar_task(self, query: str, time_of_day: str, weekdays: str) -> int:
        if not time_of_day:
            time_of_day = datetime.now().strftime("%H:%M")
        weekday_list = self._parse_weekdays(weekdays) if weekdays else list(range(7))
        delay = self._get_next_delay(datetime.now(), 24 * 60 * 60, time_of_day, weekday_list)
        return await self.deferred_execution_helper(
            query,
            delay,
            -1,  # Not used
            -1,
            time_of_day=time_of_day,
            weekdays=weekday_list,
        )

    async def tool_get_scheduled_tasks(self) -> dict:
        return self.ctx.session.scheduled_tasks

    async def tool_cancel_scheduled_task(self, task_id: int) -> bool:
        if task_id in self.ctx.session.scheduled_tasks:
            del self.ctx.session.scheduled_tasks[task_id]
            return True
        return False
