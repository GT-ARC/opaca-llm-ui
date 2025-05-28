"""
Simple approach, directly communicating with an LLM, acquires available tools/services dynamically and uses the tools in a loop until it thinks the user's request is fulfilled, using an LLM's tool parameter.
Works for both, GPT and vLLM.
Parameter "ask_policy" can be used to determine how much confirmation the LLM will require.
"""

from .simple_tools_routes import SimpleToolsBackend
