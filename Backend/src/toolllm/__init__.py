"""
LLM Client using LangChain together with the "tools" feature of newer LLM models.
Does not require "understanding" actions and "parsing" results, and can execute
multiple tools per iteration, but actions have to fulfill some requirements to
be translatable to tools (e.g. no cycles in data type definitions).
Currently only works with GPT-4.
"""

from .tool_routes import ToolLLMBackend
from .tool_method import ToolMethod, ToolMethodRegistry
from .tool_method_llama import ToolMethodLlama
from .tool_method_openai import ToolMethodOpenAI
