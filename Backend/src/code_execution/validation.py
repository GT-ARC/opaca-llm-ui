"""Static analysis validation via pylint, bandit, and mypy."""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

Parser = Callable[[subprocess.CompletedProcess, str], list[str]]

PYLINT_CMD = [
    "pylint",
    "--output-format=text",
    "--msg-template={path}:{line}:{column}: [{msg_id}({symbol})] {msg}",
    "--disable=all",
    "--enable=E,W,F",
]
BANDIT_CMD = ["bandit", "-r", "-f", "json"]
MYPY_CMD = [
    "mypy",
    "--show-error-codes",
    "--show-column-numbers",
    "--no-color-output",
]


def parse_pylint(proc: subprocess.CompletedProcess, temp_path: str) -> list[str]:
    issues = []
    for line in (proc.stdout or "").splitlines():
        if line.strip() and ":" in line and "[" in line and "]" in line:
            issues.append(line.replace(f"{temp_path}:", "line ", 1))
    return issues


def parse_bandit(proc: subprocess.CompletedProcess, _: str) -> list[str]:
    if not (proc.stdout or "").strip():
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


def parse_mypy(proc: subprocess.CompletedProcess, temp_path: str) -> list[str]:
    issues = []
    for line in (proc.stdout or "").splitlines():
        if line.strip() and "error:" in line:
            issues.append(line.replace(f"{temp_path}:", "line ", 1))
    return issues


def run_validator(
        command: list[str],
        parser: Parser,
        code: str,
        timeout_s: int,
        run_id: str,
) -> list[str]:
    """Run a single validation tool against the given code."""
    tool_name = command[0]
    logger.debug("[ExecuteCode:%s] validator=%s start", run_id, tool_name)

    try:
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8",
        ) as temp_file:
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
            logger.debug(
                "[ExecuteCode:%s] validator=%s rc=%s stdout_len=%d stderr_len=%d",
                run_id, tool_name, proc.returncode,
                len(proc.stdout or ""), len(proc.stderr or ""),
            )
            issues = parser(proc, temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    except FileNotFoundError:
        issues = [f"{tool_name} not found in PATH."]
        logger.warning("[ExecuteCode:%s] validator=%s missing in PATH", run_id, tool_name)
    except subprocess.TimeoutExpired:
        issues = [f"{tool_name} timed out."]
        logger.warning("[ExecuteCode:%s] validator=%s timeout", run_id, tool_name)
    except Exception as e:
        issues = [f"{tool_name} failed: {e}"]
        logger.exception("[ExecuteCode:%s] validator=%s failed", run_id, tool_name)

    logger.debug("[ExecuteCode:%s] validator=%s issues=%d", run_id, tool_name, len(issues))
    return issues


async def run_all_validators(code: str, timeout_s: int, run_id: str) -> dict[str, list[str]]:
    """Run pylint, bandit, and mypy concurrently. Returns dict mapping tool name to issues."""
    pylint, bandit, mypy = await asyncio.gather(
        asyncio.to_thread(run_validator, PYLINT_CMD, parse_pylint, code, timeout_s, run_id),
        asyncio.to_thread(run_validator, BANDIT_CMD, parse_bandit, code, timeout_s, run_id),
        asyncio.to_thread(run_validator, MYPY_CMD, parse_mypy, code, timeout_s, run_id),
    )
    result = {"pylint": pylint, "bandit": bandit, "mypy": mypy}
    logger.info(
        "[ExecuteCode:%s] validation pylint=%d bandit=%d mypy=%d",
        run_id, len(result["pylint"]), len(result["bandit"]), len(result["mypy"]),
    )
    return result