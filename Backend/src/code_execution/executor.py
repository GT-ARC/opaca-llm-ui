"""Main code execution orchestrator for the Pyodide sandbox."""

import asyncio
import logging
import uuid

from ..models import ExecutionResult
from .util import trim_for_log, transform_notebook_style

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_TIMEOUT = 124
EXIT_INTERNAL_ERROR = 125
EXIT_SANDBOX_UNAVAILABLE = 126


class CodeExecutor:
    """Executes Python code in a sandboxed Pyodide environment."""

    async def execute_code(self, code: str, timeout_s: int = 10) -> ExecutionResult:
        run_id = uuid.uuid4().hex[:12]
        prepared_code = transform_notebook_style(code)

        logger.info("[ExecuteCode:%s] called timeout_s=%r code_len=%d", run_id, timeout_s, len(code))

        # set up Pyodide. This can fail if Pyodide is not installed
        try:
            from langchain_sandbox import PyodideSandbox
            sandbox = PyodideSandbox(
                allow_read=True,
                allow_write=True,
                allow_net=True,
                node_modules_dir="auto",
                stateful=True,
            )
        except Exception as e:
            return self._build_result(
                stdout="",
                stderr=f"Initializing Pyodide sandbox failed: {e}",
                exit_code=EXIT_SANDBOX_UNAVAILABLE,
                timed_out=False,
                run_id=run_id,
            )

        # once set up, try to run the actual code...
        try:
            invocation = sandbox.execute(
                code=prepared_code,
                timeout_seconds=float(timeout_s),
                memory_limit_mb=1024,
            )
            response = await asyncio.wait_for(invocation, timeout=timeout_s)
            stdout, stderr, status = response.stdout, response.stderr, response.status

            return self._build_result(
                stdout=stdout,
                stderr=stderr,
                exit_code=EXIT_RUNTIME_ERROR if status == "error" else EXIT_SUCCESS,
                timed_out=False,
                run_id=run_id,
            )

        except asyncio.TimeoutError:
            logger.warning("[ExecuteCode:%s] sandbox timeout after %ds", run_id, timeout_s)
            return self._build_result(
                stdout="",
                stderr="[timeout]",
                exit_code=EXIT_TIMEOUT,
                timed_out=True,
                run_id=run_id,
            )
        except Exception as exc:
            logger.exception("[ExecuteCode:%s] sandbox execution failed", run_id)
            return self._build_result(
                stdout="",
                stderr=f"Pyodide execution failed: {exc}",
                exit_code=EXIT_INTERNAL_ERROR,
                timed_out=False,
                run_id=run_id,
            )

    @staticmethod
    def _build_result(stdout: str, stderr: str, exit_code: int, timed_out: bool, run_id: str) -> ExecutionResult:
        return ExecutionResult(
            run_id=run_id,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
        )
