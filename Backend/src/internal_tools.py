"""
Wrapper for different internal tools, to be provided to the OPACA LLM as "actions" like OPACA,
but implemented directly in the backend.

Those tools are then added to the OPACA Proxy's actions in the AbstractMethod's get_tools method.
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
from typing import Callable, TYPE_CHECKING
from textwrap import dedent

from .file_utils import register_bytes_as_uploaded_file, filename_from_url_and_type
from .models import SessionData, Chat, PushAdvert, PushMessage, ScheduledTask, QueryResponse
from .code_execution import CodeExecutor, extract_code_block, PYODIDE_CODE_PROMPT, PYODIDE_CODE_RETRY_PROMPT

if TYPE_CHECKING:
    from .abstract_method import AbstractMethod


TIME_FORMAT = "%b %d %Y %H:%M"
INTERNAL_TOOLS_AGENT_NAME = "LLM-Assistant"

logger = logging.getLogger(__name__)


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    required_params: list[str] | None = None
    result: str
    function: Callable
    requires_code_execution: bool = False


class InternalTools:

    def __init__(self, session: SessionData, agent_method: type['AbstractMethod']):
        self.session = session
        self.agent_method = agent_method
        self.code_executor = CodeExecutor()
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
            InternalTool(
                name="ReadFileFromUrl",
                description="Downloads a file from a URL and uploads it to the backend to be used by the LLM.",
                params={"url": "string"},
                result="object",
                function=self.tool_read_file_from_url,
            ),
            # CODE EXECUTION
            InternalTool(
                name="ExecuteCode",
                description="Execute a given Python code snippet directly in a Pyodide sandbox. Prefer SolveWithCode unless you already have a specific snippet. Libraries may not be installed. Bare expressions are printed like in Jupyter. Returns stdout, stderr, status (e.g. success, error,  timeout), and run_id.",
                params={"code": "string", "timeout_s": "integer"},
                required_params=["code"],
                result="object",
                function=self.code_executor.execute_code,
                requires_code_execution=True,
            ),
            InternalTool(
                name="SolveWithCode",
                description="Solve a computational task by generating and executing Python code in a Pyodide sandbox. Describe the task in plain language. Code is generated, executed, and retried automatically when execution fails. Returns runtime execution artifacts, generated_code, attempts, and attempt_history.",
                params={"task": "string", "timeout_s": "integer", "max_code_retries": "integer"},
                required_params=["task"],
                result="object",
                function=self.tool_solve_with_code,
                requires_code_execution=True,
            ),
        ]

    def available_tools(self) -> list[InternalTool]:
        if CodeExecutor.available:
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
                            "required": key in (tool.required_params if tool.required_params is not None else tool.params.keys())
                        }
                        for key, val in tool.params.items()
                    },
                    "result": {"type": tool.result, "required": True}
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
                }
            }
            for tool in self.available_tools()
        ]

    async def call_internal_tool(self, tool: str, parameters: dict):
        """get callback method for internal tool matching the name and call with given parameters"""
        tool_def = next((t for t in self.available_tools() if t.name == tool), None)
        if tool_def is None:
            raise ValueError(f"Internal tool '{tool}' is not available")
        return await tool_def.function(**parameters)

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
                result = QueryResponse(query=query)
                result.make_error_response(e)

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
        """shorthand for calling AgentMethod.query, without streaming, chat, or internal tools"""
        response = QueryResponse(query=query)
        method_impl = self.agent_method(self.session, Chat(chat_id=''), response, streaming=False)
        return await method_impl.query()

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


    async def tool_solve_with_code(self, task: str, timeout_s: int = 10, max_code_retries: int = 2) -> dict:
        """
        Generate Python code for *task* via an internal LLM call, execute it
        in the Pyodide sandbox, and — if execution fails — retry up to
        max_code_retries times with the error fed back to the LLM.
        """
        prompt = PYODIDE_CODE_PROMPT.format(task=task)
        attempt_history: list[dict] = []

        for attempt in range(1, max_code_retries + 2):
            # 1. Ask the LLM to write code
            llm_response = await self.query_method(prompt)
            code = extract_code_block(llm_response.content)

            if not code:
                attempt_history.append(
                    {"attempt": attempt, "error": "LLM did not produce any code."}
                )
                logger.warning(
                    "SolveWithCode attempt %d/%d failed: No code generated",
                    attempt, 1 + max_code_retries,
                )
                prompt = PYODIDE_CODE_PROMPT.format(task=task) + "\n" + (
                    "Your previous reply did not contain executable Python code. "
                    "Respond with ONLY valid Python code."
                )
                continue

            # 2. Execute in sandbox, add to history
            exec_result = await self.code_executor.execute_code(code=code, timeout_s=timeout_s)
            attempt_history.append(
                {"attempt": attempt, "generated_code": code, **exec_result.model_dump()}
            )

            # 3. Success → return immediately
            if exec_result.status == "success":
                return { **attempt_history.pop(), "previous_attempts": attempt_history }

            # 4. Failure → build retry prompt
            logger.warning(
                "SolveWithCode attempt %d/%d failed. status=%s stderr=%s",
                attempt, 1 + max_code_retries,
                exec_result.status, exec_result.stderr,
            )
            prompt = PYODIDE_CODE_PROMPT.format(task=task) + "\n" + PYODIDE_CODE_RETRY_PROMPT.format(
                code=code,
                status=exec_result.status,
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
            )

        return { **attempt_history.pop(), "previous_attempts": attempt_history }
