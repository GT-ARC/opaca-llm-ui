import asyncio

import pytest

from src.code_execution import CodeExecutor
from src.internal_tools import INTERNAL_TOOLS_AGENT_NAME, InternalTools
from src.models import QueryResponse, ScheduledTask, SessionData


class DummyMethod:
    NAME = "dummy-method"

    def __init__(self, session, streaming=False):
        self.session = session
        self.streaming = streaming

    async def query(self, query, chat):
        return QueryResponse(query=query, content="dummy response")


EXPECTED_TOOL_NAMES = [
    "ScheduleIntervalTask",
    "ScheduleCalendarTask",
    "GetScheduledTasks",
    "CancelScheduleTask",
    "GatherUserInfo",
    "SearchChats",
    "ReadFileFromUrl",
    "ExecuteCode",
    "SolveWithCode",
]


EXPECTED_DESCRIPTIONS = {
    "ScheduleIntervalTask": "Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the interval in the query itself. Tasks can be executed just once or recurring. A negative value for 'repetitions' is interpreted as 'forever'. The delay should be a time in seconds for the first execution from now, and interval between executions, if applicable. Returns task ID",
    "ScheduleCalendarTask": "Schedule some action to be executed forever on a calendar schedule. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. Do not include the time or weekdays in the query itself. The task repeats forever. 'weekdays' must be a comma-separated list like 'Mon,Fri'; Pass an empty string for 'weekdays' to make it a daily task. For 'time_of_day' pass the local time in format 'HH:MM', or an empty string to use the current local time. Returns task ID",
    "GetScheduledTasks": "Get list of scheduled tasks, including task IDs and details",
    "CancelScheduleTask": "Cancel a previously scheduled task. Return true/false whether a task with this ID existed.",
    "GatherUserInfo": "Compiles a short expose about the current chat user from this and past interactions, their personal situation, preferences, etc..",
    "SearchChats": "Search this and past interactions about information on the given topic and summarize the findings.",
    "ReadFileFromUrl": "Downloads a file from a URL and uploads it to the backend to be used by the LLM.",
    "ExecuteCode": "Execute a given Python code snippet directly in a Pyodide sandbox. Prefer SolveWithCode unless you already have a specific snippet. Libraries may not be installed. Bare expressions are printed like in Jupyter. Returns stdout, stderr, status (e.g. success, error,  timeout), and run_id.",
    "SolveWithCode": "Solve a computational task by generating and executing Python code in a Pyodide sandbox. Describe the task in plain language. Code is generated, executed, and retried automatically when execution fails. Returns runtime execution artifacts, generated_code, attempts, and attempt_history.",
}


EXPECTED_PARAMS = {
    "ScheduleIntervalTask": {"query": "string", "delay_seconds": "integer", "repetitions": "integer"},
    "ScheduleCalendarTask": {"query": "string", "time_of_day": "string", "weekdays": "string"},
    "GetScheduledTasks": {},
    "CancelScheduleTask": {"task_id": "integer"},
    "GatherUserInfo": {},
    "SearchChats": {"search_query": "string"},
    "ReadFileFromUrl": {"url": "string"},
    "ExecuteCode": {"code": "string", "timeout_s": "integer"},
    "SolveWithCode": {"task": "string", "timeout_s": "integer", "max_code_retries": "integer"},
}


EXPECTED_RESULTS = {
    "ScheduleIntervalTask": "integer",
    "ScheduleCalendarTask": "integer",
    "GetScheduledTasks": "object",
    "CancelScheduleTask": "boolean",
    "GatherUserInfo": "string",
    "SearchChats": "string",
    "ReadFileFromUrl": "object",
    "ExecuteCode": "object",
    "SolveWithCode": "object",
}


@pytest.fixture
def code_executor_available():
    previous = CodeExecutor.available
    CodeExecutor.available = True
    try:
        yield
    finally:
        CodeExecutor.available = previous


def make_internal_tools():
    return InternalTools(SessionData(), DummyMethod)


def test_internal_tool_definitions_are_unchanged(code_executor_available):
    internal_tools = make_internal_tools()

    assert [tool.name for tool in internal_tools.tools] == EXPECTED_TOOL_NAMES
    for tool in internal_tools.tools:
        assert tool.description == EXPECTED_DESCRIPTIONS[tool.name]
        assert tool.params == EXPECTED_PARAMS[tool.name]
        assert tool.result == EXPECTED_RESULTS[tool.name]


def test_simple_schema_is_unchanged(code_executor_available):
    schema = make_internal_tools().get_internal_tools_simple()

    assert list(schema) == [INTERNAL_TOOLS_AGENT_NAME]
    tools = schema[INTERNAL_TOOLS_AGENT_NAME]
    assert [tool["name"] for tool in tools] == EXPECTED_TOOL_NAMES

    execute_code = next(tool for tool in tools if tool["name"] == "ExecuteCode")
    assert execute_code["parameters"] == {
        "code": {"type": "string", "required": True},
        "timeout_s": {"type": "integer", "required": False},
    }
    assert execute_code["result"] == {"type": "object", "required": True}

    schedule = next(tool for tool in tools if tool["name"] == "ScheduleIntervalTask")
    assert all(param["required"] is True for param in schedule["parameters"].values())


def test_openai_schema_is_unchanged(code_executor_available):
    schema = make_internal_tools().get_internal_tools_openai()

    assert [tool["name"] for tool in schema] == [
        f"{INTERNAL_TOOLS_AGENT_NAME}--{name}" for name in EXPECTED_TOOL_NAMES
    ]

    solve_with_code = next(tool for tool in schema if tool["name"].endswith("--SolveWithCode"))
    assert solve_with_code["parameters"] == {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "timeout_s": {"type": "integer"},
            "max_code_retries": {"type": "integer"},
        },
        "additionalProperties": False,
        "required": ["task"],
    }


def test_code_tools_are_hidden_when_code_executor_is_unavailable():
    previous = CodeExecutor.available
    CodeExecutor.available = False
    try:
        internal_tools = make_internal_tools()
        assert [tool.name for tool in internal_tools.available_tools()] == EXPECTED_TOOL_NAMES[:-2]
    finally:
        CodeExecutor.available = previous


def test_call_internal_tool_dispatches_by_action_name(code_executor_available):
    session = SessionData()
    session.scheduled_tasks[7] = ScheduledTask(
        method=DummyMethod.NAME,
        task_id=7,
        query="test",
        next_time="May 06 2026 10:00",
        interval=60,
        repetitions=1,
    )

    result = asyncio.run(
        InternalTools(session, DummyMethod).call_internal_tool("CancelScheduleTask", {"task_id": 7})
    )

    assert result is True
    assert 7 not in session.scheduled_tasks


def test_call_internal_tool_rejects_unknown_tool(code_executor_available):
    with pytest.raises(ValueError, match="Internal tool 'DoesNotExist' is not available"):
        asyncio.run(InternalTools(SessionData(), DummyMethod).call_internal_tool("DoesNotExist", {}))


def test_resume_scheduled_task_compatibility_wrapper(code_executor_available, monkeypatch):
    internal_tools = make_internal_tools()
    task = ScheduledTask(
        method=DummyMethod.NAME,
        task_id=3,
        query="test",
        next_time="May 06 2026 10:00",
        interval=60,
        repetitions=1,
    )
    called = {}

    async def fake_resume(received_task):
        called["task"] = received_task
        return "ok"

    monkeypatch.setattr(internal_tools.scheduling, "resume_scheduled_task", fake_resume)

    result = asyncio.run(internal_tools.resume_scheduled_task(task))

    assert result == "ok"
    assert called["task"] is task
