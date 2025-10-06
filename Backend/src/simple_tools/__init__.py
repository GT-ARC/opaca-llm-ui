"""
Simple approach, directly communicating with an LLM, acquires available tools/services dynamically and uses the tools in a loop until it thinks the user's request is fulfilled, using an LLM's tool parameter.
Works for both, GPT and vLLM.
"""

from .simple_tools_routes import SimpleToolsMethod
