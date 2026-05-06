from __future__ import annotations

import logging

from ..code_execution import PYODIDE_CODE_PROMPT, PYODIDE_CODE_RETRY_PROMPT, extract_code_block
from .context import InternalToolContext
from .definitions import InternalTool


logger = logging.getLogger(__name__)


class CodeTools:
    def __init__(self, ctx: InternalToolContext):
        self.ctx = ctx

    def tools(self) -> list[InternalTool]:
        return [
            InternalTool(
                name="ExecuteCode",
                description="Execute a given Python code snippet directly in a Pyodide sandbox. Prefer SolveWithCode unless you already have a specific snippet. Libraries may not be installed. Bare expressions are printed like in Jupyter. Returns stdout, stderr, status (e.g. success, error,  timeout), and run_id.",
                params={"code": "string", "timeout_s": "integer"},
                required_params=["code"],
                result="object",
                function=self.ctx.code_executor.execute_code,
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

    async def tool_solve_with_code(self, task: str, timeout_s: int = 10, max_code_retries: int = 2) -> dict:
        """
        Generate Python code for *task* via an internal LLM call, execute it
        in the Pyodide sandbox, and if execution fails retry up to
        max_code_retries times with the error fed back to the LLM.
        """
        prompt = PYODIDE_CODE_PROMPT.format(task=task)
        attempt_history: list[dict] = []

        for attempt in range(1, max_code_retries + 2):
            # 1. Ask the LLM to write code
            llm_response = await self.ctx.query(prompt)
            code = extract_code_block(llm_response.content)

            if not code:
                attempt_history.append(
                    {"attempt": attempt, "error": "LLM did not produce any code."}
                )
                logger.warning(
                    "SolveWithCode attempt %d/%d failed: No code generated",
                    attempt,
                    1 + max_code_retries,
                )
                prompt = PYODIDE_CODE_PROMPT.format(task=task) + "\n" + (
                    "Your previous reply did not contain executable Python code. "
                    "Respond with ONLY valid Python code."
                )
                continue

            # 2. Execute in sandbox, add to history
            exec_result = await self.ctx.code_executor.execute_code(code=code, timeout_s=timeout_s)
            attempt_history.append(
                {"attempt": attempt, "generated_code": code, **exec_result.model_dump()}
            )

            # 3. Success - return immediately
            if exec_result.status == "success":
                return {**attempt_history.pop(), "previous_attempts": attempt_history}

            # 4. Failure - build retry prompt
            logger.warning(
                "SolveWithCode attempt %d/%d failed. status=%s stderr=%s",
                attempt,
                1 + max_code_retries,
                exec_result.status,
                exec_result.stderr,
            )
            prompt = PYODIDE_CODE_PROMPT.format(task=task) + "\n" + PYODIDE_CODE_RETRY_PROMPT.format(
                code=code,
                status=exec_result.status,
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
            )

        return {**attempt_history.pop(), "previous_attempts": attempt_history}
