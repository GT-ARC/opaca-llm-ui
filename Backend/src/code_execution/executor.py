"""Main code execution orchestrator for the Pyodide sandbox."""

import asyncio
import inspect
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

    async def execute_code(self, code: str, timeout_s: int = 10) -> dict:
        run_id = uuid.uuid4().hex[:12]
        prepared_code = transform_notebook_style(code)

        logger.info("[ExecuteCode:%s] called timeout_s=%r code_len=%d", run_id, timeout_s, len(code))

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

        try:
            return await self._run_with_pyodide(
                sandbox=sandbox,
                run_id=run_id,
                prepared_code=prepared_code,
                timeout_s=timeout_s,
            )
        finally:
            await self._close_sandbox(sandbox, run_id)

    async def _run_with_pyodide(self, sandbox, run_id: str, prepared_code: str, timeout_s: int) -> dict:
        try:
            stdout, stderr, result_obj, status, normalization = await self._run_once(
                sandbox=sandbox,
                prepared_code=prepared_code,
                timeout_s=timeout_s,
                run_id=run_id,
                attempt=1,
            )
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

    async def _run_once(self, sandbox, prepared_code: str, timeout_s: int, run_id: str, attempt: int) -> tuple[str, str, object, str | None, str]:
        logger.debug(
            "[ExecuteCode:%s] sandbox execute attempt=%d timeout_seconds=%s memory_limit_mb=%d",
            run_id,
            attempt,
            float(timeout_s),
            1024,
        )
        invocation = sandbox.execute(
            code=prepared_code,
            timeout_seconds=float(timeout_s),
            memory_limit_mb=1024,
        )

        if inspect.isawaitable(invocation):
            response = await asyncio.wait_for(invocation, timeout=timeout_s)
        else:
            response = invocation

        stdout, stderr, result_obj, status, normalization = self._normalize_response(response)
        if stderr:
            logger.debug(
                "[ExecuteCode:%s] pyodide stderr(attempt=%d)=%s",
                run_id,
                attempt,
                trim_for_log(stderr),
            )
        return stdout, stderr, result_obj, status, normalization

    @staticmethod
    def _normalize_response(response: object) -> tuple[str, str, object, str | None, str]:
        if isinstance(response, str):
            return response, "", None, None, "str"

        status = getattr(response, "status", None)
        stdout = getattr(response, "stdout", "") or getattr(response, "output", "") or ""
        stderr = getattr(response, "stderr", "") or ""
        result_obj = getattr(response, "result", None)
        attrs = [
            attr for attr in ("stdout", "output", "stderr", "status", "result", "error", "message", "detail")
            if getattr(response, attr, None) not in (None, "")
        ]
        normalization = f"attrs({','.join(attrs)})" if attrs else type(response).__name__

        if not stderr and isinstance(result_obj, dict):
            for key in ("stderr", "error", "message", "detail", "traceback"):
                value = result_obj.get(key)
                if isinstance(value, str) and value.strip():
                    stderr = value
                    normalization += f"+result.{key}"
                    break

        if not stderr:
            for attr in ("error", "message", "detail"):
                value = getattr(response, attr, None)
                if isinstance(value, str) and value.strip():
                    stderr = value
                    normalization += f"+attr.{attr}"
                    break

        if not stdout and result_obj is not None:
            stdout = str(result_obj)
            normalization += "+result_to_stdout"

        return stdout, stderr, result_obj, status, normalization

    @staticmethod
    async def _close_sandbox(sandbox, run_id: str) -> None:
        close_async = getattr(sandbox, "aclose", None)
        close_sync = getattr(sandbox, "close", None)
        try:
            if callable(close_async):
                await close_async()
            elif callable(close_sync):
                close_sync()
        except Exception:
            logger.exception("[ExecuteCode:%s] sandbox close failed", run_id)

    @staticmethod
    def _build_result(stdout: str, stderr: str, exit_code: int, timed_out: bool, run_id: str) -> dict:
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
            run_id=run_id,
        ).model_dump()
