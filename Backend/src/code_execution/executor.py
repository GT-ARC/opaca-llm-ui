"""Main code execution orchestrator for the Pyodide sandbox."""

import asyncio
import inspect
import logging
import uuid

from .execution_proof import ProofToken
from ..models import ExecutionResult
from .util import trim_for_log, transform_notebook_style

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_PROOF_FAILED = 6
EXIT_TIMEOUT = 124
EXIT_INTERNAL_ERROR = 125
EXIT_SANDBOX_UNAVAILABLE = 126


def _init_sandbox(sandbox_cls, run_id: str):
    kwargs = {
        "allow_read": True,
        "allow_write": True,
        "allow_net": True,
        "node_modules_dir": "auto",
        "stateful": True,
    }
    logger.warning("[ExecuteCode:%s] sandbox init kwargs=%s", run_id, kwargs)
    return sandbox_cls(**kwargs)


class CodeExecutor:
    """Executes Python code in a sandboxed Pyodide environment."""

    def __init__(self):
        self._sandbox_cls = None
        self._sandbox_import_error = None

    def _get_sandbox_cls(self):
        if self._sandbox_cls is not None:
            return self._sandbox_cls
        if self._sandbox_import_error is not None:
            return None

        try:
            from langchain_sandbox import PyodideSandbox
        except Exception as e:
            logger.error("PyodideSandbox import failed", exc_info=True)
            self._sandbox_import_error = e
            return None

        self._sandbox_cls = PyodideSandbox
        return PyodideSandbox

    async def execute_code(self, code: str, timeout_s: int = 10) -> dict:
        run_id = uuid.uuid4().hex[:12]
        proof = ProofToken.generate(run_id)
        prepared_code = proof.build_prelude() + "\n" + transform_notebook_style(code) + "\n"

        logger.info("[ExecuteCode:%s] called timeout_s=%r code_len=%d", run_id, timeout_s, len(code))

        sandbox_cls = self._get_sandbox_cls()
        if sandbox_cls is None:
            return self._build_result(
                stdout="",
                stderr=f"Pyodide import failed: {self._sandbox_import_error}",
                exit_code=EXIT_SANDBOX_UNAVAILABLE,
                timed_out=False,
                run_id=run_id,
            )

        try:
            sandbox = _init_sandbox(sandbox_cls, run_id)
        except Exception as exc:
            logger.exception("[ExecuteCode:%s] sandbox init failed", run_id)
            return self._build_result(
                stdout="",
                stderr=f"Pyodide sandbox initialization failed: {exc}",
                exit_code=EXIT_SANDBOX_UNAVAILABLE,
                timed_out=False,
                run_id=run_id,
            )

        try:
            return await self._run_with_pyodide(
                sandbox=sandbox,
                run_id=run_id,
                prepared_code=prepared_code,
                proof=proof,
                timeout_s=timeout_s,
            )
        finally:
            await self._close_sandbox(sandbox, run_id)

    async def _run_with_pyodide(
            self,
            sandbox,
            run_id: str,
            prepared_code: str,
            proof: ProofToken,
            timeout_s: int,
    ) -> dict:

        try:
            stdout, stderr, result_obj, status, normalization = await self._run_once(
                sandbox=sandbox,
                prepared_code=prepared_code,
                timeout_s=timeout_s,
                run_id=run_id,
                attempt=1,
            )
            proof_observed = proof.extract_from_result_or_stdout(result_obj, stdout)
            proof_verified = proof.matches(proof_observed)

            if not proof_verified:
                logger.warning("[ExecuteCode:%s] retrying once because proof is missing", run_id)
                await asyncio.sleep(0.2)
                retry_stdout, retry_stderr, retry_result_obj, retry_status, retry_normalization = await self._run_once(
                    sandbox=sandbox,
                    prepared_code=prepared_code,
                    timeout_s=timeout_s,
                    run_id=run_id,
                    attempt=2,
                )
                if not retry_stderr and stderr:
                    retry_stderr = stderr
                stdout, stderr, result_obj, status, normalization = (
                    retry_stdout,
                    retry_stderr,
                    retry_result_obj,
                    retry_status,
                    retry_normalization,
                )
                proof_observed = proof.extract_from_result_or_stdout(result_obj, stdout)
                proof_verified = proof.matches(proof_observed)

            stdout = proof.strip_from_stdout(stdout)
            if proof_verified:
                return self._build_result(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=EXIT_RUNTIME_ERROR if status == "error" else EXIT_SUCCESS,
                    timed_out=False,
                    run_id=run_id,
                    proof_verified=True,
                )

            logger.warning(
                "[ExecuteCode:%s] proof verification failed status=%r normalization=%s observed=%s stderr=%s",
                run_id,
                status,
                normalization,
                proof_observed,
                trim_for_log(stderr),
            )
            detail = "Execution proof could not be verified."
            return self._build_result(
                stdout=stdout,
                stderr=f"{stderr}\n{detail}" if stderr else detail,
                exit_code=EXIT_PROOF_FAILED,
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

    async def _run_once(
            self,
            sandbox,
            prepared_code: str,
            timeout_s: int,
            run_id: str,
            attempt: int,
    ) -> tuple[str, str, object, str | None, str]:
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
    def _build_result(
            stdout: str,
            stderr: str,
            exit_code: int,
            timed_out: bool,
            run_id: str,
            proof_verified: bool = False,
    ) -> dict:
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
            run_id=run_id,
            proof_verified=proof_verified,
        ).model_dump()
