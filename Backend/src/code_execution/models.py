"""Data models for code execution results."""


class ExecutionResult:
    """Consistent return type for all execution paths."""

    def __init__(
            self,
            stdout: str,
            stderr: str,
            exit_code: int,
            timed_out: bool,
            run_id: str = "",
            validation: dict[str, list[str]] | None = None,
            execution_backend: str = "pyodide",
            proof_verified: bool = False,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.run_id = run_id
        self.validation = validation or {}
        self.execution_backend = execution_backend  # TODO remove
        self.proof_verified = proof_verified

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "run_id": self.run_id,
            "validation": self.validation,
            "execution_backend": self.execution_backend,
            "proof_verified": self.proof_verified,
        }
