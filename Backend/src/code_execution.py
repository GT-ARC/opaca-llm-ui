"""Code execution module with sandboxed Python execution."""

import asyncio
import logging
import uuid
import ast
from textwrap import dedent

from .models import ExecutionResult

logger = logging.getLogger(__name__)


PYODIDE_CODE_PROMPT = dedent("""\
    You are a Python code generator. Write code to solve the task below.
    The code runs in a Pyodide sandbox.

    ## Sandbox Environment
    - Works like a Jupyter notebook cell: the last expression's repr is
      captured automatically. Use print() for all intentional output.
    - There is NO network access (requests, urllib, etc. will fail).
    - There is NO persistent file system — do not read/write files.
    - Do NOT call input() or any interactive/blocking function.

    ## Pre-installed Libraries
    Standard-library modules are available, including:
      math, statistics, decimal, fractions, itertools, collections,
      functools, json, re, datetime, textwrap, random, …

    To install an additional pure-Python package at runtime:
        import micropip
        await micropip.install("package-name")
    Only pure-Python wheels are supported; C-extension packages may fail.
    
    ## Output Guidelines
    - Always print clear, labelled results:  print(f"Area: {{area:.2f}} m²")
    - Round floats to reasonable precision.
    - For multiple results, label each line.
    - Do NOT try to display plots/images — compute and print values instead.
    - If the task is ambiguous, state assumptions in a comment, then compute.

    ## Task
    {task}

    Respond with ONLY valid Python code. No markdown fences, no explanations.
""")

PYODIDE_CODE_RETRY_PROMPT = dedent("""\
    Your previous code failed to execute cleanly in the Pyodide sandbox. Fix it and try again.

    ## Previous Code
    ```python
    {code}
    ```

    ## Previous Execution
    status: {status}

    stdout:
    {stdout}

    stderr:
    {stderr}

    Respond with ONLY the corrected Python code. No markdown fences, no explanations.
""")


class CodeExecutor:
    """Executes Python code in a sandboxed Pyodide environment."""

    warmup_task: asyncio.Task | None = None
    available: bool | None = None

    async def warmup(self) -> None:
        result = await self._execute_code("print('pyodide-ready')", timeout_s=60)
        if result.status == "success":
            CodeExecutor.available = True
            logger.info("Pyodide sandbox warm-up completed")
        elif result.status.startswith("Initializing Pyodide sandbox failed"):
            CodeExecutor.available = False
            logger.warning("Pyodide sandbox unavailable: %s", result.status)
        else:
            CodeExecutor.available = True
            logger.warning("Pyodide sandbox warm-up failed: %s", result.status)

    async def execute_code(self, code: str, timeout_s: int = 10) -> ExecutionResult:
        if CodeExecutor.warmup_task is not None:
            await asyncio.shield(CodeExecutor.warmup_task)
        if not CodeExecutor.available:
            return ExecutionResult(run_id="-1", status="Pyodide sandbox unavailable",)
        return await self._execute_code(code, timeout_s)

    async def _execute_code(self, code: str, timeout_s: int = 10) -> ExecutionResult:
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


def transform_notebook_style(code: str) -> str:
    """Wrap the last expression statement so its result gets printed.

    Mimics Jupyter notebook behavior: if the final statement is a bare
    expression (e.g. a function call, variable name, literal), its
    non-None result is printed via repr().

    Assignments, function defs, loops, etc. are left untouched.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Let the sandbox report the syntax error, don't interfere
        return code

    if not tree.body:
        return code

    last = tree.body[-1]
    if not isinstance(last, ast.Expr):
        return code

    # Reconstruct: everything before the last statement stays as-is,
    # the last expression gets wrapped.
    lines = code.splitlines(keepends=True)
    prefix = "".join(lines[: last.lineno - 1])
    expr_source = ast.unparse(last.value)

    wrapped = (
        f"__notebook_result__ = {expr_source}\n"
        f"if __notebook_result__ is not None:\n"
        f"    print(repr(__notebook_result__))\n"
    )

    return prefix + wrapped


def extract_code_block(text: str) -> str:
    """Extract Python code from an LLM response, stripping markdown fences if present."""
    import re
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
