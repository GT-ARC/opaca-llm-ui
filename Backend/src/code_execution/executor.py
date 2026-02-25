"""Main code execution orchestrator.

Handles Pyodide sandbox execution with proof verification.
Delegates proof verification, validation, and utilities to sibling modules.
"""

import asyncio
import inspect
import logging
import subprocess
import uuid

from .models import ExecutionResult
from .execution_proof import ProofToken
from .util import is_probable_pyodide_bootstrap, trim_for_log, transform_notebook_style
from .validation import run_all_validators

logger = logging.getLogger(__name__)

# Exit codes
EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_BLOCKED_BY_VALIDATION = 3
EXIT_PROOF_FAILED = 6
EXIT_TIMEOUT = 124
EXIT_INTERNAL_ERROR = 125
EXIT_SANDBOX_INIT_FAILED = 126
EXIT_SANDBOX_IMPORT_FAILED = 127


class CodeExecutor:
    """Executes Python code in a sandboxed Pyodide environment.

    Injects a proof token into the code, runs it via langchain_sandbox's
    PyodideSandbox, then verifies the token appeared in stdout to confirm
    the sandbox actually executed the code.
    """

    def __init__(self):
        self._paths = None
        self._sandbox_cls = None
        self._sandbox_import_error = None

    def _get_paths(self) -> dict:
        if self._paths is None:
            self._paths = self._setup_sandbox_paths()
        return self._paths

    def _get_sandbox_cls(self):
        """Cache the PyodideSandbox class import.

        Returns the class on success, None on failure.
        Import error is stored, so we don't retry every call.
        """
        if self._sandbox_cls is not None:
            return self._sandbox_cls
        if self._sandbox_import_error is not None:
            return None
        try:
            from langchain_sandbox import PyodideSandbox
            self._sandbox_cls = PyodideSandbox
            return PyodideSandbox
        except Exception as e:
            logger.error("PyodideSandbox import failed", exc_info=True)
            self._sandbox_import_error = e
            return None

    async def execute_code(self, code: str, timeout_s: int = 10) -> dict:
        run_id = uuid.uuid4().hex[:12]
        proof = ProofToken.generate(run_id)
        transformed_code = transform_notebook_style(code or "")
        prepared_code = proof.build_prelude() + "\n" + transformed_code + "\n"

        logger.info(
            "[ExecuteCode:%s] called timeout_s=%r code_len=%d",
            run_id, timeout_s, len(code or ""),
        )

        # --- Validation ---
        validation = await run_all_validators(code or "", timeout_s, run_id)

        if validation["bandit"]:
            logger.warning("[ExecuteCode:%s] blocked by bandit findings", run_id)
            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout="",
                stderr="Execution blocked by validation (Bandit findings present).",
                exit_code=EXIT_BLOCKED_BY_VALIDATION,
                timed_out=False,
            )

        # --- Sandbox import ---
        sandbox_cls = self._get_sandbox_cls()
        if sandbox_cls is None:
            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout="",
                stderr=f"Pyodide import failed: {self._sandbox_import_error}",
                exit_code=EXIT_SANDBOX_IMPORT_FAILED,
                timed_out=False,
            )

        # --- Sandbox init ---
        paths = self._get_paths()
        sandbox = self._init_sandbox(sandbox_cls, run_id, paths)
        if sandbox is None:
            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout="",
                stderr="Pyodide sandbox initialization failed.",
                exit_code=EXIT_SANDBOX_INIT_FAILED,
                timed_out=False,
            )

        # --- Execute ---
        return await self._run_with_pyodide(
            sandbox=sandbox,
            run_id=run_id,
            prepared_code=prepared_code,
            proof=proof,
            validation=validation,
            timeout_s=timeout_s,
            paths=paths,
        )

    # ------------------------------------------------------------------
    # Pyodide execution
    # ------------------------------------------------------------------

    async def _run_with_pyodide(
            self,
            sandbox,
            run_id: str,
            prepared_code: str,
            proof: ProofToken,
            validation: dict[str, list[str]],
            timeout_s: int,
            paths: dict[str, str],
    ) -> dict:
        """Run code in Pyodide sandbox, verify proof, handle retry on bootstrap noise."""
        execute_fn = sandbox.execute
        execute_sig = inspect.signature(execute_fn)
        execute_params = set(execute_sig.parameters.keys())
        logger.debug(
            "[ExecuteCode:%s] sandbox execute signature=%s",
            run_id, str(execute_sig),
        )

        call_mode = self._determine_call_mode(execute_params)
        logger.debug("[ExecuteCode:%s] sandbox execute call_mode=%s", run_id, call_mode)

        pyodide_attempts: list[dict] = []

        try:
            logger.debug("[ExecuteCode:%s] sandbox execute start", run_id)

            stdout, stderr, resp_result, pyodide_status = (
                await self._run_pyodide_once(
                    execute_fn=execute_fn,
                    execute_params=execute_params,
                    call_mode=call_mode,
                    prepared_code=prepared_code,
                    timeout_s=timeout_s,
                    run_id=run_id,
                    attempt=1,
                    pyodide_attempts=pyodide_attempts,
                )
            )
            first_stderr = stderr
            exit_code = EXIT_RUNTIME_ERROR if pyodide_status == "error" else EXIT_SUCCESS

            proof_observed = proof.extract_from_result_or_stdout(resp_result, stdout)
            proof_valid = proof.matches(proof_observed)

            logger.info(
                "[ExecuteCode:%s] sandbox execute done pyodide_status=%r "
                "exit_code=%d stdout_len=%d stderr_len=%d proof_valid=%s",
                run_id, pyodide_status, exit_code,
                len(stdout), len(stderr), proof_valid,
            )

            # --- Retry on bootstrap noise ---
            if (
                    not proof_valid
                    and pyodide_status != "error"
                    and is_probable_pyodide_bootstrap(stderr)
            ):
                logger.warning(
                    "[ExecuteCode:%s] detected pyodide bootstrap noise; retrying once",
                    run_id,
                )
                await asyncio.sleep(0.2)

                stdout, stderr, resp_result, pyodide_status = (
                    await self._run_pyodide_once(
                        execute_fn=execute_fn,
                        execute_params=execute_params,
                        call_mode=call_mode,
                        prepared_code=prepared_code,
                        timeout_s=timeout_s,
                        run_id=run_id,
                        attempt=2,
                        pyodide_attempts=pyodide_attempts,
                    )
                )
                exit_code =EXIT_RUNTIME_ERROR if pyodide_status == "error" else EXIT_SUCCESS
                proof_observed = proof.extract_from_result_or_stdout(resp_result, stdout)
                proof_valid = proof.matches(proof_observed)
                if not stderr and first_stderr:
                    stderr = first_stderr

                logger.warning(
                    "[ExecuteCode:%s] sandbox retry done exit_code=%d "
                    "stdout_len=%d stderr_len=%d proof_valid=%s",
                    run_id, exit_code, len(stdout), len(stderr), proof_valid,
                )

            # --- Evaluate result ---
            if proof_valid:
                return self._build_result(
                    run_id=run_id,
                    validation=validation,
                    stdout=proof.strip_from_stdout(stdout),
                    stderr=stderr,
                    exit_code=exit_code,
                    timed_out=False,
                    execution_backend="pyodide",
                    proof_verified=True,
                )

            # Proof failed — gather diagnostics and return error
            self._log_proof_failure_diagnostics(
                run_id=run_id,
                pyodide_status=pyodide_status,
                stderr=stderr,
                first_stderr=first_stderr,
                proof=proof,
                proof_observed=proof_observed,
                prepared_code=prepared_code,
                timeout_s=timeout_s,
                paths=paths,
            )

            stderr_text = (stderr or first_stderr or "").strip()
            detail = "Execution proof could not be verified."
            if stderr_text:
                stderr_text = f"{stderr_text}\n{detail}"
            else:
                stderr_text = detail

            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout=proof.strip_from_stdout(stdout),
                stderr=stderr_text,
                exit_code=EXIT_PROOF_FAILED,
                timed_out=False,
                execution_backend="pyodide",
            )

        except asyncio.TimeoutError:
            logger.warning(
                "[ExecuteCode:%s] sandbox timeout after %ds", run_id, timeout_s,
            )
            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout="",
                stderr="[timeout]",
                exit_code=EXIT_TIMEOUT,
                timed_out=True,
            )
        except Exception as e:
            logger.exception("[ExecuteCode:%s] sandbox execution failed", run_id)
            return self._build_result(
                run_id=run_id,
                validation=validation,
                stdout="",
                stderr=f"Pyodide execution failed: {e}",
                exit_code=EXIT_INTERNAL_ERROR,
                timed_out=False,
            )
        finally:
            await self._close_sandbox(sandbox, run_id)

    async def _run_pyodide_once(
            self,
            execute_fn,
            execute_params: set[str],
            call_mode: str,
            prepared_code: str,
            timeout_s: int,
            run_id: str,
            attempt: int,
            pyodide_attempts: list[dict],
    ) -> tuple[str, str, object, str | None]:
        """Single Pyodide execution attempt.

        Returns (stdout, stderr, result_obj, status).
        """
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
            run_id, attempt, execute_kwargs,
        )

        if call_mode == "positional":
            invocation = execute_fn(prepared_code)
        else:
            invocation = execute_fn(**execute_kwargs)

        if inspect.isawaitable(invocation):
            response = await asyncio.wait_for(invocation, timeout=timeout_s)
        else:
            response = invocation

        logger.debug(
            "[ExecuteCode:%s] sandbox response(attempt=%d) type=%s repr=%s",
            run_id, attempt,
            type(response).__name__,
            repr(response)[:1200],
        )

        stdout, stderr, result_obj, status = self._normalize_response(response, run_id)

        if stderr:
            logger.warning(
                "[ExecuteCode:%s] pyodide stderr(attempt=%d)=%s",
                run_id, attempt, trim_for_log(stderr),
            )

        pyodide_attempts.append({
            "attempt": attempt,
            "status": status,
            "stdout_len": len(stdout),
            "stderr_len": len(stderr),
            "result_type": type(result_obj).__name__ if result_obj is not None else "None",
            "response_type": type(response).__name__,
        })

        return stdout, stderr, result_obj, status

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_response(
            response: object, run_id: str,
    ) -> tuple[str, str, object, str | None]:
        """Extract (stdout, stderr, result_obj, status) from a sandbox response.

        Handles three known shapes:
        1. dict with stdout/stderr keys
        2. Pydantic model with model_dump()
        3. Object with attributes or plain string
        """
        stdout = ""
        stderr = ""
        result_obj = None
        status = getattr(response, "status", None)

        if isinstance(response, dict):
            logger.debug(
                "[ExecuteCode:%s] response keys=%s", run_id, sorted(response.keys()),
            )
            stdout = response.get("stdout", "") or response.get("output", "") or ""
            stderr = response.get("stderr", "") or response.get("error", "") or ""
            if status is None:
                status = response.get("status")
            result_obj = (
                response.get("result")
                if "result" in response else
                response.get("value")
                if "value" in response else
                response.get("data")
            )

        elif hasattr(response, "model_dump"):
            try:
                dumped = response.model_dump()
                logger.debug(
                    "[ExecuteCode:%s] model_dump keys=%s",
                    run_id, sorted(dumped.keys()),
                )
                stdout = dumped.get("stdout", "") or dumped.get("output", "") or ""
                stderr = dumped.get("stderr", "") or dumped.get("error", "") or ""
                if not stderr:
                    stderr = dumped.get("message", "") or dumped.get("detail", "") or ""
                if status is None:
                    status = dumped.get("status")
                result_obj = dumped.get("result")
                if not stdout:
                    for key in ("text", "message", "content"):
                        val = dumped.get(key)
                        if isinstance(val, str):
                            stdout = val
                            break
            except Exception:
                pass

            if not stdout:
                stdout = (
                        getattr(response, "stdout", "")
                        or getattr(response, "output", "")
                        or ""
                )
            if not stderr:
                stderr = (
                        getattr(response, "stderr", "")
                        or getattr(response, "error", "")
                        or ""
                )
            if result_obj is None:
                result_obj = getattr(response, "result", None)

        elif isinstance(response, str):
            stdout = response

        else:
            stdout = (
                    getattr(response, "stdout", "")
                    or getattr(response, "output", "")
                    or ""
            )
            stderr = (
                    getattr(response, "stderr", "")
                    or getattr(response, "error", "")
                    or ""
            )
            result_obj = getattr(response, "result", None)

        # Extract stderr from nested result dict
        if not stderr and isinstance(result_obj, dict):
            for key in ("stderr", "error", "message", "detail", "traceback"):
                value = result_obj.get(key)
                if isinstance(value, str) and value.strip():
                    stderr = value
                    break

        # Last resort: check response attributes directly
        if not stderr:
            for attr in ("error", "message", "detail"):
                candidate = getattr(response, attr, None)
                if isinstance(candidate, str) and candidate.strip():
                    stderr = candidate
                    break

        # Promote result to stdout if stdout is still empty
        if not stdout and result_obj is not None:
            stdout = str(result_obj)

        return stdout, stderr, result_obj, status

    # ------------------------------------------------------------------
    # Sandbox init and teardown
    # ------------------------------------------------------------------

    def _init_sandbox(self, sandbox_cls, run_id: str, paths: dict[str, str]):
        """Instantiate PyodideSandbox with compatible kwargs.

        Returns the sandbox instance, or None on failure.
        """
        try:
            init_sig = inspect.signature(sandbox_cls.__init__)
            init_params = set(init_sig.parameters.keys())
            logger.warning(
                "[ExecuteCode:%s] sandbox init signature=%s",
                run_id, str(init_sig),
            )

            kwargs = {}
            if "sessions_dir" in init_params:
                kwargs["sessions_dir"] = paths["sessions_dir"]
            if "allow_read" in init_params:
                kwargs["allow_read"] = True
            if "allow_write" in init_params:
                kwargs["allow_write"] = True
            if "allow_net" in init_params:
                kwargs["allow_net"] = True
            elif "allow_network" in init_params:
                kwargs["allow_network"] = True
            if "node_modules_dir" in init_params:
                kwargs["node_modules_dir"] = "auto"
            if "stateful" in init_params:
                kwargs["stateful"] = True

            logger.debug("[ExecuteCode:%s] sandbox init kwargs=%s", run_id, kwargs)
            return sandbox_cls(**kwargs)
        except Exception:
            logger.exception("[ExecuteCode:%s] sandbox init failed", run_id)
            return None

    @staticmethod
    async def _close_sandbox(sandbox, run_id: str) -> None:
        """Close sandbox, tolerating missing or failing close methods."""
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

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def _log_proof_failure_diagnostics(
            self,
            run_id: str,
            pyodide_status: str | None,
            stderr: str,
            first_stderr: str,
            proof: ProofToken,
            proof_observed: dict | None,
            prepared_code: str,
            timeout_s: int,
            paths: dict[str, str],
    ) -> None:
        """
        Log diagnostics when proof verification fails (Debugging only).
        Deno smoke test runs in background to avoid blocking the response.
        """
        logger.warning(
            "[ExecuteCode:%s] proof verification failed "
            "pyodide_status=%r expected=%s observed=%s",
            run_id, pyodide_status, proof.expected, proof_observed,
        )

        if pyodide_status != "error":
            return

        stderr_text = stderr or first_stderr or ""
        stderr_lc = stderr_text.lower()
        markers = [
            "error:", "notcapable", "requires read access",
            "requires write access", "permission denied",
            "uncaught (in promise)", "traceback", "exception",
        ]
        matched = [m for m in markers if m in stderr_lc]
        if matched:
            logger.warning("[ExecuteCode:%s] stderr markers=%s", run_id, matched)
        if not stderr:
            logger.warning(
                "[ExecuteCode:%s] status='error' but stderr is empty", run_id,
            )

        # Run Deno probe in background
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(
                None,
                self._run_deno_smoke_test, run_id, prepared_code, timeout_s, paths,
            )
        except Exception:
            logger.debug("[ExecuteCode:%s] could not schedule background deno probe", run_id)

    def _run_deno_smoke_test(
            self,
            run_id: str,
            prepared_code: str,
            timeout_s: int,
            paths: dict[str, str],
    ) -> str:
        """Run Deno diagnostic commands and return a summary string for logging."""
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
                    f"{label}: rc={proc.returncode} "
                    f"stdout={trim_for_log(proc.stdout, 800)!r} "
                    f"stderr={trim_for_log(proc.stderr, 800)!r}"
                )
            except FileNotFoundError as e:
                reports.append(f"{label}: FileNotFoundError: {e}")
            except subprocess.TimeoutExpired:
                reports.append(f"{label}: timeout after {timeout}s")
            except Exception as e:
                reports.append(f"{label}: {type(e).__name__}: {e}")

        code_timeout = max(20, min(timeout_s, 60))

        _run_cmd(["deno", "--version"], "deno_version", timeout=8)
        _run_cmd(
            [
                "deno", "run", "-A",
                "jsr:@langchain/pyodide-sandbox", "-c", "print('PING')",
            ],
            "pyodide_cli_smoke",
            timeout=20,
        )
        _run_cmd(
            [
                "deno", "run", "-A",
                "jsr:@langchain/pyodide-sandbox", "-c", prepared_code,
            ],
            "pyodide_cli_user_code",
            timeout=code_timeout,
        )
        _run_cmd(
            [
                "deno", "run",
                "--node-modules-dir=auto",
                f"--allow-read={','.join(paths['allowed_read'])}",
                f"--allow-write={','.join(paths['allowed_write'])}",
                f"--allow-net={','.join(PYODIDE_ALLOWED_HOSTS)}",
                "jsr:@langchain/pyodide-sandbox",
                "-c", prepared_code,
            ],
            "pyodide_cli_restricted",
            timeout=code_timeout,
        )

        logger.debug("[ExecuteCode:%s] deno probe=%s", run_id, " | ".join(reports))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_call_mode(execute_params: set[str]) -> str:
        if "code" in execute_params:
            return "kw:code"
        if "input" in execute_params:
            return "kw:input"
        if "source" in execute_params:
            return "kw:source"
        return "positional"

    @staticmethod
    def _setup_sandbox_paths() -> dict:
        from pathlib import Path

        app_root = Path(__file__).resolve().parent.parent
        sessions_dir = app_root / "data" / "sandbox_sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        pyodide_runtime_dir = sessions_dir / "pyodide_runtime"
        pyodide_runtime_dir.mkdir(parents=True, exist_ok=True)
        pyodide_node_modules_dir = pyodide_runtime_dir / "node_modules"
        pyodide_node_modules_dir.mkdir(parents=True, exist_ok=True)

        allowed_rw = [
            str(sessions_dir),
            str(pyodide_runtime_dir),
            str(pyodide_node_modules_dir),
            "/tmp",
        ]
        allowed_read = allowed_rw + [
            "/app/node_modules",
            "/app/node_modules/.deno",
            "/app/.cache",
            "/app/.cache/deno",
            "/root/.cache",
            "/root/.cache/deno",
        ]
        allowed_write = allowed_rw + [
            "/app/node_modules/.deno",
            "/app/.cache/deno",
            "/root/.cache/deno",
        ]

        return {
            "sessions_dir": str(sessions_dir),
            "allowed_read": allowed_read,
            "allowed_write": allowed_write,
        }

    @staticmethod
    def _build_result(
            run_id: str,
            validation: dict[str, list[str]],
            stdout: str,
            stderr: str,
            exit_code: int,
            timed_out: bool,
            execution_backend: str = "pyodide",
            proof_verified: bool = False,
    ) -> dict:
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timed_out=timed_out,
            run_id=run_id,
            validation=validation,
            execution_backend=execution_backend,
            proof_verified=proof_verified,
        ).to_dict()
