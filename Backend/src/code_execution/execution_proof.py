"""Execution proof injection, extraction, and verification.

The proof mechanism works by injecting a print statement into the code
that outputs a known JSON token. After execution, we verify that token
appeared in stdout — confirming the sandbox actually ran our code.
"""

import json
import uuid


class ProofToken:
    """Represents a unique proof token for a single execution run."""

    def __init__(self, sentinel: str, run_id: str, nonce: str):
        self.sentinel = sentinel
        self.run_id = run_id
        self.nonce = nonce
        self.prefix = "__OPACA_PROOF__:"

    @classmethod
    def generate(cls, run_id: str) -> "ProofToken":
        return cls(
            sentinel="SAGE_EXECUTE_CODE_SENTINEL_V1",
            run_id=run_id,
            nonce=uuid.uuid4().hex[:10],
        )

    @property
    def expected(self) -> dict:
        return {
            "sentinel": self.sentinel,
            "run_id": self.run_id,
            "nonce": self.nonce,
        }

    def build_prelude(self) -> str:
        """Python code that prints the proof token to stdout."""
        return (
            "import json as __sage_json\n"
            f"__sage_execute_code_sentinel__ = {json.dumps(self.sentinel)}\n"
            f"__sage_execute_code_run_id__ = {json.dumps(self.run_id)}\n"
            f"__sage_execute_code_proof__ = {json.dumps(self.expected)}\n"
            f"print({json.dumps(self.prefix)} + "
            f"__sage_json.dumps(__sage_execute_code_proof__, sort_keys=True))\n"
        )

    def extract_from_stdout(self, stdout: str) -> dict | None:
        """Find and parse the proof dict from stdout.

        Checks line-by-line first (fast path), then scans for inline
        occurrences (handles case where user code prints on same line).
        """
        text = stdout or ""

        decoder = json.JSONDecoder()
        search_at = 0
        while True:
            idx = text.find(self.prefix, search_at)
            if idx < 0:
                break
            remainder = text[idx + len(self.prefix):]
            payload = remainder.lstrip()
            try:
                parsed, _ = decoder.raw_decode(payload)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            search_at = idx + len(self.prefix) + 1
        return None

    def extract_from_result_or_stdout(
            self, result_obj: object, stdout: str
    ) -> dict | None:
        """Try to find the proof in a sandbox result object first, then stdout."""
        if isinstance(result_obj, dict):
            if {"sentinel", "run_id", "nonce"}.issubset(result_obj.keys()):
                return {
                    "sentinel": result_obj.get("sentinel"),
                    "run_id": result_obj.get("run_id"),
                    "nonce": result_obj.get("nonce"),
                }
        return self.extract_from_stdout(stdout)

    def matches(self, observed: dict | None) -> bool:
        """Check whether an observed proof dict matches what we expected."""
        if not isinstance(observed, dict):
            return False
        return (
                observed.get("sentinel") == self.sentinel
                and observed.get("run_id") == self.run_id
                and observed.get("nonce") == self.nonce
        )

    def strip_from_stdout(self, stdout: str) -> str:
        """Remove the proof token and all preceding runtime noise from stdout.

        The proof prelude is injected at the top of the code, so anything
        that appears before it in stdout is sandbox bootstrapping noise
        (e.g. Pyodide package download messages). User output starts
        after the proof line.
        """
        text = stdout or ""

        decoder = json.JSONDecoder()
        search_at = 0
        while True:
            idx = text.find(self.prefix, search_at)
            if idx < 0:
                break
            remainder = text[idx + len(self.prefix):]
            payload = remainder.lstrip()
            ws = len(remainder) - len(payload)
            try:
                parsed, consumed = decoder.raw_decode(payload)
                if isinstance(parsed, dict):
                    # Everything after the proof JSON is user output
                    after_proof = idx + len(self.prefix) + ws + consumed
                    return text[after_proof:].strip()
            except (json.JSONDecodeError, ValueError):
                pass
            search_at = idx + len(self.prefix) + 1

        # No proof found — return as-is
        return text.strip()
