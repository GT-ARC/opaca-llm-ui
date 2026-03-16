"""Small stateless helpers for code execution."""

import ast


def trim_for_log(text: str | None, max_chars: int = 1200) -> str:
    """Truncate text for log output, preserving head and tail."""
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    head = max_chars // 2
    tail = max_chars - head
    hidden = len(value) - max_chars
    return f"{value[:head]} ... <snip {hidden} chars> ... {value[-tail:]}"


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
