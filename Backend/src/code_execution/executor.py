"""Main code execution orchestrator for the Pyodide sandbox."""

import asyncio
import logging
import uuid

from ..models import ExecutionResult
from .util import transform_notebook_style

logger = logging.getLogger(__name__)


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
            return ExecutionResult(run_id=run_id, status=f"Initializing Pyodide sandbox failed: {e}")

        # once set up, try to run the actual code...
        try:
            invocation = sandbox.execute(
                code=prepared_code,
                timeout_seconds=float(timeout_s),
                memory_limit_mb=1024,
            )
            response = await asyncio.wait_for(invocation, timeout=timeout_s+5)
            return ExecutionResult(
                run_id=run_id,
                stdout=response.stdout,
                stderr=response.stderr,
                status=response.status,
            )

        except Exception as exc:
            logger.exception("[ExecuteCode:%s] sandbox execution failed", run_id)
            return ExecutionResult(run_id=run_id, status=f"Pyodide execution failed: {exc}")
