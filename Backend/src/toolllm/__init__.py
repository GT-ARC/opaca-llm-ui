"""
LLM Client using the "tools" feature of newer LLM models.
Does not require "understanding" actions and "parsing" results, and can execute
multiple tools per iteration, but actions have to fulfill some requirements to
be translatable to tools (e.g. no cycles in data type definitions).
Works with GPT models and vLLM.
"""

from .tool_routes import ToolLLMMethod
