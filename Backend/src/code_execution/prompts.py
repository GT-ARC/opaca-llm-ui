"""Prompt templates for LLM-assisted code generation targeting the Pyodide sandbox."""

from textwrap import dedent

MAX_CODE_RETRIES = 2

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
    Your previous code failed. Fix it and try again.

    ## Previous Code
    ```python
    {code}
    ```

    ## Error Output
    stdout:
    {stdout}

    stderr:
    {stderr}

    Respond with ONLY the corrected Python code. No markdown fences, no explanations.
""")
