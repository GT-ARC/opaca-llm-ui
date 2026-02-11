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
import inspect
import os
import requests
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from math import ceil

from pydantic import BaseModel
from typing import Callable
from textwrap import dedent

from .file_utils import register_bytes_as_uploaded_file, filename_from_url_and_type
from .models import SessionData, Chat, PushAdvert, PushMessage, ScheduledTask, QueryResponse


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
            InternalTool(
                name="ReadFileFromUrl",
                description="Downloads a file from a URL and uploads it to the backend to be used by the LLM.",
                params={"url": "string"},
                result="object",
                function=self.tool_read_file_from_url,
            ),
            InternalTool(
                name="ExecuteCode",
                description="Runs python code in a sandbox with pre-installed packages only. Timeout parameter is optional.",
                params={"language": "string", "code": "string", "timeout_s": "integer"},
                required_params=["language", "code"],
                result="object",
                function=self.execute_code,
            )
        ]

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
                    "required": tool.required_params if tool.required_params is not None else list(tool.params),
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

    async def execute_code(self, language: str, code: str, timeout_s: int = 10) -> dict:
        run_id = uuid.uuid4().hex[:12]
        use_subprocess_fallback = False
        sentinel_value = "OPACA_EXECUTE_CODE_SENTINEL_V1"
        proof_prefix = "__OPACA_PROOF__:"
        proof_expected = {
            "sentinel": sentinel_value,
            "run_id": run_id,
            "nonce": uuid.uuid4().hex[:10],
        }
        injected_prelude = (
            "import json as __opaca_json\n"
            f"__opaca_execute_code_sentinel__ = {json.dumps(sentinel_value)}\n"
            f"__opaca_execute_code_run_id__ = {json.dumps(run_id)}\n"
            f"__opaca_execute_code_proof__ = {json.dumps(proof_expected)}\n"
            f"print({json.dumps(proof_prefix)} + __opaca_json.dumps(__opaca_execute_code_proof__, sort_keys=True))\n"
        )
        # Keep proof in stdout only; returning a Python dict as final expression can break
        # some Pyodide wrappers during result serialization.
        prepared_code = injected_prelude + "\n" + (code or "") + "\n"
        logger.warning(
            "[ExecuteCode:%s] called language=%r timeout_s=%r code_len=%d",
            run_id, language, timeout_s, len(code or "")
        )
        language = language.strip().lower()
        if language != "python":
            logger.warning("[ExecuteCode:%s] unsupported language=%r", run_id, language)
            return {"stdout": "", "stderr": f"Unsupported language: {language}", "exit_code": 2, "timed_out": False}

        try:
            timeout_s = max(1, int(timeout_s))
        except Exception:
            timeout_s = 10
        logger.warning("[ExecuteCode:%s] normalized timeout_s=%d", run_id, timeout_s)

        # Validation adapted from llm-auto-codegen-main static analyzer.
        def _run_validator(command: list[str], parser) -> list[str]:
            issues: list[str] = []
            tool_name = command[0]
            logger.warning("[ExecuteCode:%s] validator=%s start", run_id, tool_name)
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".py",
                    delete=False,
                    encoding="utf-8",
                ) as temp_file:
                    # Validate user code only. Runtime prelude is internal plumbing.
                    temp_file.write(code or "")
                    temp_path = temp_file.name
                try:
                    proc = subprocess.run(
                        command + [temp_path],
                        capture_output=True,
                        text=True,
                        timeout=min(timeout_s, 30),
                        check=False,
                    )
                    logger.warning(
                        "[ExecuteCode:%s] validator=%s rc=%s stdout_len=%d stderr_len=%d",
                        run_id,
                        tool_name,
                        proc.returncode,
                        len(proc.stdout or ""),
                        len(proc.stderr or ""),
                    )
                    issues = parser(proc, temp_path)
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            except FileNotFoundError:
                issues = [f"{command[0]} not found in PATH."]
                logger.warning("[ExecuteCode:%s] validator=%s missing in PATH", run_id, tool_name)
            except subprocess.TimeoutExpired:
                issues = [f"{command[0]} timed out."]
                logger.warning("[ExecuteCode:%s] validator=%s timeout", run_id, tool_name)
            except Exception as e:
                issues = [f"{command[0]} failed: {e}"]
                logger.exception("[ExecuteCode:%s] validator=%s failed", run_id, tool_name)
            logger.warning("[ExecuteCode:%s] validator=%s issues=%d", run_id, tool_name, len(issues))
            return issues

        def _parse_pylint(proc: subprocess.CompletedProcess, temp_path: str) -> list[str]:
            msg_template = "{path}:{line}:{column}: [{msg_id}({symbol})] {msg}"
            _ = msg_template  # Keep template context from original project.
            issues = []
            for line in (proc.stdout or "").splitlines():
                if line.strip() and ":" in line and "[" in line and "]" in line:
                    issues.append(line.replace(f"{temp_path}:", "line ", 1))
            return issues

        def _parse_bandit(proc: subprocess.CompletedProcess, _: str) -> list[str]:
            if not proc.stdout.strip():
                return []
            try:
                report = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return [f"Bandit output parse error: {proc.stdout[:200]}..."]
            issues = []
            for result in report.get("results", []):
                issues.append(
                    f"[{result.get('issue_severity', '?')}/{result.get('issue_confidence', '?')}] "
                    f"{result.get('issue_text', 'Issue')} "
                    f"(ID: {result.get('test_id', '?')}, Line: {result.get('line_number', '?')})"
                )
            return issues

        def _parse_mypy(proc: subprocess.CompletedProcess, temp_path: str) -> list[str]:
            issues = []
            for line in (proc.stdout or "").splitlines():
                if line.strip() and "error:" in line:
                    issues.append(line.replace(f"{temp_path}:", "line ", 1))
            return issues

        pylint_cmd = [
            "pylint",
            "--output-format=text",
            "--msg-template={path}:{line}:{column}: [{msg_id}({symbol})] {msg}",
            "--disable=all",
            "--enable=E,W,F",
        ]
        bandit_cmd = ["bandit", "-r", "-f", "json"]
        mypy_cmd = ["mypy", "--show-error-codes", "--show-column-numbers", "--no-color-output"]

        validation = {
            "pylint": _run_validator(pylint_cmd, _parse_pylint),
            "bandit": _run_validator(bandit_cmd, _parse_bandit),
            "mypy": _run_validator(mypy_cmd, _parse_mypy),
        }
        logger.warning(
            "[ExecuteCode:%s] validation summary pylint=%d bandit=%d mypy=%d",
            run_id,
            len(validation["pylint"]),
            len(validation["bandit"]),
            len(validation["mypy"]),
        )

        app_root = Path(__file__).resolve().parent.parent
        sessions_dir = app_root / "data" / "sandbox_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        pyodide_runtime_dir = sessions_dir / "pyodide_runtime"
        pyodide_runtime_dir.mkdir(parents=True, exist_ok=True)
        pyodide_node_modules_dir = pyodide_runtime_dir / "node_modules"
        pyodide_node_modules_dir.mkdir(parents=True, exist_ok=True)
        allowed_rw_paths = [
            str(sessions_dir),
            str(pyodide_runtime_dir),
            str(pyodide_node_modules_dir),
            "/tmp",
        ]
        # Pyodide runtime reads wasm/assets from Deno's node_modules cache under /app.
        # Keep this narrow instead of enabling unrestricted filesystem read access.
        allowed_read_paths = allowed_rw_paths + [
            "/app/node_modules",
            "/app/node_modules/.deno",
            "/app/.cache",
            "/app/.cache/deno",
            "/root/.cache",
            "/root/.cache/deno",
        ]
        allowed_write_paths = allowed_rw_paths + [
            "/app/node_modules/.deno",
            "/app/.cache/deno",
            "/root/.cache/deno",
        ]
        logger.warning("[ExecuteCode:%s] sandbox sessions_dir=%s", run_id, str(sessions_dir))

        def _extract_proof_from_stdout(stdout: str) -> dict | None:
            text = stdout or ""
            decoder = json.JSONDecoder()

            # Fast path: proof on its own line.
            for line in text.splitlines():
                if line.startswith(proof_prefix):
                    payload = line[len(proof_prefix):].strip()
                    try:
                        parsed = json.loads(payload)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass

            # Robust path: proof token appears inline in a larger stdout blob.
            search_at = 0
            while True:
                idx = text.find(proof_prefix, search_at)
                if idx < 0:
                    break
                remainder = text[idx + len(proof_prefix):]
                ws = len(remainder) - len(remainder.lstrip())
                payload = remainder.lstrip()
                try:
                    parsed, _ = decoder.raw_decode(payload)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                search_at = idx + len(proof_prefix) + max(ws, 1)
            return None

        def _strip_proof_line(stdout: str) -> str:
            text = stdout or ""
            decoder = json.JSONDecoder()
            parts: list[str] = []
            cursor = 0

            while True:
                idx = text.find(proof_prefix, cursor)
                if idx < 0:
                    parts.append(text[cursor:])
                    break

                parts.append(text[cursor:idx])
                remainder = text[idx + len(proof_prefix):]
                ws = len(remainder) - len(remainder.lstrip())
                payload = remainder.lstrip()
                json_start = idx + len(proof_prefix) + ws

                try:
                    parsed, consumed = decoder.raw_decode(payload)
                    if isinstance(parsed, dict):
                        cursor = json_start + consumed
                        continue
                except Exception:
                    pass

                # Not a parseable proof payload; keep the prefix text as normal output.
                parts.append(proof_prefix)
                cursor = idx + len(proof_prefix)

            return "".join(parts).strip()

        def _trim_for_log(text: str | None, max_chars: int = 1200) -> str:
            value = (text or "").strip()
            if len(value) <= max_chars:
                return value
            head = max_chars // 2
            tail = max_chars - head
            hidden = len(value) - max_chars
            return f"{value[:head]} ... <snip {hidden} chars> ... {value[-tail:]}"

        def _proof_from_result_or_stdout(result_obj, out_text: str) -> dict | None:
            observed = None
            if isinstance(result_obj, dict):
                if {"sentinel", "run_id", "nonce"}.issubset(result_obj.keys()):
                    observed = {
                        "sentinel": result_obj.get("sentinel"),
                        "run_id": result_obj.get("run_id"),
                        "nonce": result_obj.get("nonce"),
                    }
            if observed is None:
                observed = _extract_proof_from_stdout(out_text)
            return observed

        def _proof_matches_expected(observed: dict | None) -> bool:
            if not isinstance(observed, dict):
                return False
            return (
                observed.get("sentinel") == proof_expected.get("sentinel")
                and observed.get("run_id") == proof_expected.get("run_id")
                and observed.get("nonce") == proof_expected.get("nonce")
            )

        def _result(
            stdout: str,
            stderr: str,
            exit_code: int,
            timed_out: bool,
            proof_observed: dict | None = None,
            pyodide_status: str | None = None,
            pyodide_response: dict | None = None,
            execution_backend: str = "pyodide",
            fallback_reason: str | None = None,
            pyodide_attempts_local: list[dict] | None = None,
        ) -> dict:
            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "validation": validation,
                "run_id": run_id,
                "sandbox_sentinel": sentinel_value,
                "execution_proof_expected": proof_expected,
                "execution_proof_observed": proof_observed,
                "pyodide_status": pyodide_status,
                "pyodide_response": pyodide_response,
                "execution_backend": execution_backend,
                "fallback_reason": fallback_reason,
                "pyodide_attempts": pyodide_attempts_local or [],
            }

        def _is_probable_pyodide_bootstrap(stderr_text: str) -> bool:
            text = (stderr_text or "").lower()
            if "download" not in text:
                return False
            fatal_markers = [
                "error:",
                "notcapable",
                "requires read access",
                "traceback",
                "exception",
                "permission denied",
                "deno is not installed",
                "not in path",
                "module not found",
                "syntaxerror",
            ]
            return not any(marker in text for marker in fatal_markers)

        def _run_deno_smoke_test(code_snippet: str | None = None) -> str:
            reports: list[str] = []

            def _run_cmd(cmd: list[str], label: str, timeout: int = 15) -> None:
                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    reports.append(
                        f"{label}: rc={proc.returncode} stdout={_trim_for_log(proc.stdout, 800)!r} stderr={_trim_for_log(proc.stderr, 800)!r}"
                    )
                except FileNotFoundError as e:
                    reports.append(f"{label}: FileNotFoundError: {e}")
                except subprocess.TimeoutExpired:
                    reports.append(f"{label}: timeout after {timeout}s")
                except Exception as e:
                    reports.append(f"{label}: {type(e).__name__}: {e}")

            _run_cmd(["deno", "--version"], "deno_version", timeout=8)
            _run_cmd(
                ["deno", "run", "-A", "jsr:@langchain/pyodide-sandbox", "-c", "print('PING')"],
                "pyodide_cli_smoke",
                timeout=20,
            )
            if code_snippet is not None:
                _run_cmd(
                    ["deno", "run", "-A", "jsr:@langchain/pyodide-sandbox", "-c", code_snippet],
                    "pyodide_cli_user_code",
                    timeout=max(20, min(timeout_s, 60)),
                )
                restricted_cmd = [
                    "deno",
                    "run",
                    "--node-modules-dir=auto",
                    f"--allow-read={','.join(allowed_read_paths)}",
                    f"--allow-write={','.join(allowed_write_paths)}",
                    "--allow-net",
                    "jsr:@langchain/pyodide-sandbox",
                    "-c",
                    code_snippet,
                ]
                _run_cmd(
                    restricted_cmd,
                    "pyodide_cli_user_code_restricted",
                    timeout=max(20, min(timeout_s, 60)),
                )

            return " | ".join(reports)

        def _execute_in_subprocess_fallback(
            reason: str,
            pyodide_status: str | None = None,
            pyodide_response: dict | None = None,
            pyodide_stderr: str = "",
        ) -> dict:
            logger.warning(
                "[ExecuteCode:%s] local subprocess fallback start reason=%s",
                run_id,
                reason,
            )
            try:
                with tempfile.TemporaryDirectory(
                    dir=str(sessions_dir),
                    prefix=f"exec_{run_id}_",
                ) as tmp_dir:
                    script_path = Path(tmp_dir) / "main.py"
                    script_path.write_text(prepared_code, encoding="utf-8")

                    env = {
                        "PATH": os.environ.get("PATH", ""),
                        "PYTHONUNBUFFERED": "1",
                        "PYTHONIOENCODING": "utf-8",
                        "HOME": os.environ.get("HOME", "/tmp"),
                    }

                    preexec_fn = None
                    if os.name != "nt":
                        def _set_limits() -> None:
                            try:
                                import resource
                                cpu_soft = max(1, timeout_s)
                                resource.setrlimit(resource.RLIMIT_CPU, (cpu_soft, cpu_soft + 1))
                                mem_limit = 512 * 1024 * 1024
                                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                                file_limit = 16 * 1024 * 1024
                                resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
                                resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
                            except Exception:
                                pass

                        preexec_fn = _set_limits

                    try:
                        proc = subprocess.run(
                            [sys.executable, "-I", "-B", str(script_path)],
                            capture_output=True,
                            text=True,
                            timeout=timeout_s,
                            cwd=tmp_dir,
                            env=env,
                            check=False,
                            preexec_fn=preexec_fn,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning("[ExecuteCode:%s] subprocess fallback timeout after %ds", run_id, timeout_s)
                        return _result(
                            "",
                            "[timeout]",
                            124,
                            True,
                            None,
                            pyodide_status,
                            pyodide_response,
                            execution_backend="subprocess",
                            fallback_reason=reason,
                        )

                    stdout_raw = proc.stdout or ""
                    stderr_raw = proc.stderr or ""
                    proof_observed = _proof_from_result_or_stdout(None, stdout_raw)
                    proof_valid = _proof_matches_expected(proof_observed)
                    stdout_clean = _strip_proof_line(stdout_raw)

                    logger.warning(
                        "[ExecuteCode:%s] subprocess fallback done rc=%d stdout_len=%d stderr_len=%d proof_observed=%s",
                        run_id,
                        proc.returncode,
                        len(stdout_clean),
                        len(stderr_raw),
                        bool(proof_valid),
                    )
                    if stderr_raw:
                        logger.warning(
                            "[ExecuteCode:%s] subprocess stderr preview=%s",
                            run_id,
                            _trim_for_log(stderr_raw),
                        )

                    if not proof_valid:
                        detail = "Execution proof missing from subprocess response."
                        merged_stderr = stderr_raw.strip()
                        if pyodide_stderr:
                            merged_stderr = (merged_stderr + "\n[pyodide stderr]\n" + pyodide_stderr).strip()
                        merged_stderr = (merged_stderr + "\n" + detail).strip() if merged_stderr else detail
                        return _result(
                            stdout_clean,
                            merged_stderr,
                            6,
                            False,
                            None,
                            pyodide_status,
                            pyodide_response,
                            execution_backend="subprocess",
                            fallback_reason=reason,
                        )

                    merged_stderr = stderr_raw
                    if pyodide_stderr:
                        merged_stderr = (merged_stderr + "\n[pyodide stderr]\n" + pyodide_stderr).strip()

                    return _result(
                        stdout_clean,
                        merged_stderr,
                        proc.returncode,
                        False,
                        proof_observed,
                        pyodide_status,
                        pyodide_response,
                        execution_backend="subprocess",
                        fallback_reason=reason,
                    )
            except Exception as e:
                logger.exception("[ExecuteCode:%s] subprocess fallback failed", run_id)
                return _result(
                    "",
                    f"Subprocess fallback failed: {e}",
                    125,
                    False,
                    None,
                    pyodide_status,
                    pyodide_response,
                    execution_backend="subprocess",
                    fallback_reason=reason,
                )

        # Block execution on detected Bandit findings.
        if validation["bandit"]:
            logger.warning("[ExecuteCode:%s] blocked by bandit findings", run_id)
            return {
                "stdout": "",
                "stderr": "Execution blocked by validation (Bandit findings present).",
                "exit_code": 3,
                "timed_out": False,
                "validation": validation,
                "run_id": run_id,
            }

        try:
            from langchain_sandbox import PyodideSandbox
        except Exception as e:
            logger.exception("[ExecuteCode:%s] failed importing PyodideSandbox", run_id)
            if use_subprocess_fallback:
                return _execute_in_subprocess_fallback(f"Pyodide import failed: {e}")
            return _result("", f"Pyodide import failed: {e}", 127, False, execution_backend="pyodide")

        sandbox = None
        try:
            init_sig = inspect.signature(PyodideSandbox.__init__)
            init_params = set(init_sig.parameters.keys())
            logger.warning(
                "[ExecuteCode:%s] sandbox init signature=%s",
                run_id,
                str(init_sig),
            )
            sandbox_kwargs = {}
            if "sessions_dir" in init_params:
                sandbox_kwargs["sessions_dir"] = str(sessions_dir)
            if "allow_read" in init_params:
                sandbox_kwargs["allow_read"] = True
            if "allow_write" in init_params:
                sandbox_kwargs["allow_write"] = True
            if "allow_net" in init_params:
                sandbox_kwargs["allow_net"] = True
            elif "allow_network" in init_params:
                sandbox_kwargs["allow_network"] = True
            if "allow_env" in init_params:
                sandbox_kwargs["allow_env"] = True
            if "allow_run" in init_params:
                sandbox_kwargs["allow_run"] = True
            if "allow_ffi" in init_params:
                sandbox_kwargs["allow_ffi"] = True
            if "node_modules_dir" in init_params:
                # Deno expects mode values ("auto" | "manual" | "none"), not a filesystem path.
                sandbox_kwargs["node_modules_dir"] = "auto"
            if "stateful" in init_params:
                sandbox_kwargs["stateful"] = True

            logger.warning(
                "[ExecuteCode:%s] sandbox init kwargs=%s",
                run_id,
                sandbox_kwargs,
            )
            sandbox = PyodideSandbox(**sandbox_kwargs)
        except Exception as e:
            logger.exception("[ExecuteCode:%s] sandbox init failed", run_id)
            if use_subprocess_fallback:
                return _execute_in_subprocess_fallback(f"Pyodide init failed: {e}")
            return _result("", f"Pyodide init failed: {e}", 126, False, execution_backend="pyodide")

        fallback_payload: tuple[str, str | None, dict | None, str] | None = None
        pyodide_attempts: list[dict] = []

        try:
            logger.warning("[ExecuteCode:%s] sandbox execute start", run_id)
            execute_fn = sandbox.execute
            execute_sig = inspect.signature(execute_fn)
            execute_params = set(execute_sig.parameters.keys())
            logger.warning(
                "[ExecuteCode:%s] sandbox execute signature=%s",
                run_id,
                str(execute_sig),
            )

            call_mode = "positional"
            if "code" in execute_params:
                call_mode = "kw:code"
            elif "input" in execute_params:
                call_mode = "kw:input"
            elif "source" in execute_params:
                call_mode = "kw:source"
            logger.warning("[ExecuteCode:%s] sandbox execute call_mode=%s", run_id, call_mode)

            async def _run_pyodide_once(attempt: int) -> tuple[str, str, object, dict | None, str | None]:
                execute_kwargs = {}
                if call_mode == "kw:code":
                    execute_kwargs["code"] = prepared_code
                elif call_mode == "kw:input":
                    execute_kwargs["input"] = prepared_code
                elif call_mode == "kw:source":
                    execute_kwargs["source"] = prepared_code

                if "language" in execute_params:
                    execute_kwargs["language"] = "python"
                elif "lang" in execute_params:
                    execute_kwargs["lang"] = "python"
                if "timeout_seconds" in execute_params:
                    execute_kwargs["timeout_seconds"] = float(timeout_s)
                if "memory_limit_mb" in execute_params:
                    execute_kwargs["memory_limit_mb"] = 1024

                logger.warning(
                    "[ExecuteCode:%s] sandbox execute kwargs(attempt=%d)=%s",
                    run_id,
                    attempt,
                    execute_kwargs,
                )

                if call_mode == "positional":
                    invocation = execute_fn(prepared_code)
                else:
                    invocation = execute_fn(**execute_kwargs)

                if inspect.isawaitable(invocation):
                    response = await asyncio.wait_for(invocation, timeout=timeout_s)
                else:
                    response = invocation

                logger.warning(
                    "[ExecuteCode:%s] sandbox response type(attempt=%d)=%s",
                    run_id, attempt, type(response).__name__,
                )
                logger.warning(
                    "[ExecuteCode:%s] sandbox response repr(attempt=%d)=%s",
                    run_id, attempt, repr(response)[:1200],
                )
                response_dump = None

                status_local = getattr(response, "status", None)

                if isinstance(response, dict):
                    logger.warning("[ExecuteCode:%s] sandbox response keys=%s", run_id, sorted(response.keys()))
                    stdout_local = response.get("stdout", "") or response.get("output", "") or ""
                    stderr_local = response.get("stderr", "") or response.get("error", "") or ""
                    response_dump = response
                    if status_local is None:
                        status_local = response.get("status")
                    result_local = (
                        response.get("result")
                        if "result" in response else
                        response.get("value")
                        if "value" in response else
                        response.get("data")
                    )
                else:
                    stdout_local = (
                        getattr(response, "stdout", "") or
                        getattr(response, "output", "") or
                        ""
                    )
                    stderr_local = (
                        getattr(response, "stderr", "") or
                        getattr(response, "error", "") or
                        ""
                    )
                    result_local = getattr(response, "result", None)
                    if not stdout_local and not stderr_local and isinstance(response, str):
                        stdout_local = response
                    if hasattr(response, "model_dump"):
                        try:
                            dumped = response.model_dump()
                            response_dump = dumped
                            logger.warning("[ExecuteCode:%s] sandbox model_dump keys=%s", run_id, sorted(dumped.keys()))
                            stdout_local = dumped.get("stdout", "") or dumped.get("output", "") or stdout_local
                            stderr_local = dumped.get("stderr", "") or dumped.get("error", "") or stderr_local
                            if not stderr_local:
                                stderr_local = dumped.get("message", "") or dumped.get("detail", "") or ""
                            if status_local is None:
                                status_local = dumped.get("status")
                            if result_local is None:
                                result_local = dumped.get("result")
                            if not stdout_local:
                                for key in ("text", "message", "content"):
                                    val = dumped.get(key)
                                    if isinstance(val, str):
                                        stdout_local = val
                                        break
                        except Exception:
                            pass

                if not stderr_local and isinstance(result_local, dict):
                    for key in ("stderr", "error", "message", "detail", "traceback"):
                        value = result_local.get(key)
                        if isinstance(value, str) and value.strip():
                            stderr_local = value
                            break

                if not stderr_local:
                    err_attr = getattr(response, "error", None)
                    msg_attr = getattr(response, "message", None)
                    detail_attr = getattr(response, "detail", None)
                    for candidate in (err_attr, msg_attr, detail_attr):
                        if isinstance(candidate, str) and candidate.strip():
                            stderr_local = candidate
                            break

                if not stdout_local and result_local is not None:
                    stdout_local = str(result_local)

                if stderr_local:
                    logger.warning(
                        "[ExecuteCode:%s] pyodide stderr preview(attempt=%d)=%s",
                        run_id,
                        attempt,
                        _trim_for_log(stderr_local),
                    )

                pyodide_attempts.append(
                    {
                        "attempt": attempt,
                        "status": status_local,
                        "stdout_len": len(stdout_local or ""),
                        "stderr_len": len(stderr_local or ""),
                        "result_type": type(result_local).__name__ if result_local is not None else "NoneType",
                        "response_type": type(response).__name__,
                    }
                )

                return stdout_local, stderr_local, result_local, response_dump, status_local

            stdout, stderr, resp_result, response_dump, pyodide_status = await _run_pyodide_once(attempt=1)
            first_stderr = stderr
            exit_code = 0 if not stderr else 1

            proof_observed = _proof_from_result_or_stdout(resp_result, stdout)
            proof_valid = _proof_matches_expected(proof_observed)
            logger.warning("[ExecuteCode:%s] pyodide_status=%r", run_id, pyodide_status)
            logger.warning(
                "[ExecuteCode:%s] sandbox execute done exit_code=%d stdout_len=%d stderr_len=%d proof_observed=%s",
                run_id, exit_code, len(stdout), len(stderr), bool(proof_valid)
            )
            logger.warning("[ExecuteCode:%s] pyodide attempts=%s", run_id, pyodide_attempts)

            if (
                not proof_valid
                and pyodide_status != "error"
                and _is_probable_pyodide_bootstrap(stderr)
            ):
                logger.warning("[ExecuteCode:%s] detected pyodide bootstrap noise; retrying once", run_id)
                await asyncio.sleep(0.2)
                stdout, stderr, resp_result, response_dump, pyodide_status = await _run_pyodide_once(attempt=2)
                exit_code = 0 if not stderr else 1
                proof_observed = _proof_from_result_or_stdout(resp_result, stdout)
                proof_valid = _proof_matches_expected(proof_observed)
                if not stderr and first_stderr:
                    stderr = first_stderr
                logger.warning(
                    "[ExecuteCode:%s] sandbox retry done exit_code=%d stdout_len=%d stderr_len=%d proof_observed=%s",
                    run_id, exit_code, len(stdout), len(stderr), bool(proof_valid)
                )

            if not proof_valid:
                detail = "Execution proof missing from Pyodide response."
                if pyodide_status:
                    detail += f" status={pyodide_status!r}."
                if pyodide_status == "error":
                    stderr_text = (stderr or first_stderr or "")
                    stderr_lc = stderr_text.lower()
                    markers = [
                        "error:",
                        "notcapable",
                        "requires read access",
                        "requires write access",
                        "permission denied",
                        "uncaught (in promise)",
                        "traceback",
                        "exception",
                    ]
                    matched_markers = [m for m in markers if m in stderr_lc]
                    if matched_markers:
                        logger.warning("[ExecuteCode:%s] stderr markers=%s", run_id, matched_markers)
                        detail += f" Stderr markers: {matched_markers}."
                    if not stderr:
                        detail += " Sandbox returned status='error' without stderr."
                    deno_probe = _run_deno_smoke_test(prepared_code)
                    logger.warning("[ExecuteCode:%s] deno probe=%s", run_id, deno_probe)
                    detail += f" Deno probe: {deno_probe}"
                fallback_payload = (
                    detail,
                    pyodide_status,
                    response_dump if isinstance(response_dump, dict) else None,
                    stderr or first_stderr,
                )
            else:
                return _result(
                    _strip_proof_line(stdout),
                    stderr,
                    exit_code,
                    False,
                    proof_observed,
                    pyodide_status,
                    response_dump if isinstance(response_dump, dict) else None,
                    execution_backend="pyodide",
                    pyodide_attempts_local=pyodide_attempts,
                )
        except asyncio.TimeoutError:
            logger.warning("[ExecuteCode:%s] sandbox timeout after %ds", run_id, timeout_s)
            return _result("", "[timeout]", 124, True)
        except Exception as e:
            logger.exception("[ExecuteCode:%s] sandbox execution failed", run_id)
            fallback_payload = (f"Pyodide execution failed: {e}", None, None, "")
        finally:
            close_async = getattr(sandbox, "aclose", None)
            close_sync = getattr(sandbox, "close", None)
            try:
                if callable(close_async):
                    await close_async()
                elif callable(close_sync):
                    close_sync()
                logger.warning("[ExecuteCode:%s] sandbox closed", run_id)
            except Exception:
                logger.exception("[ExecuteCode:%s] sandbox close failed", run_id)

        if fallback_payload is not None:
            reason, status, response, pyodide_stderr = fallback_payload
            if use_subprocess_fallback:
                return _execute_in_subprocess_fallback(reason, status, response, pyodide_stderr)
            combined_stderr = pyodide_stderr.strip()
            if combined_stderr:
                combined_stderr = f"{combined_stderr}\n{reason}"
            else:
                combined_stderr = reason
            return _result(
                "",
                combined_stderr,
                6,
                False,
                None,
                status,
                response,
                execution_backend="pyodide",
                fallback_reason=reason,
                pyodide_attempts_local=pyodide_attempts,
            )

        return _result("", "Execution failed for unknown reason.", 125, False, pyodide_attempts_local=pyodide_attempts)
