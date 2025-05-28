"""
Simple approach, directly communicating with an LLM, acquiring available tools/services dynamically and using the tools in a loop until it thinks the user's request is fulfilled, parsing the LLM's
response for action invocations in JSON format and calling those along the way.
Works for both, GPT and vLLM.
Parameter "ask_policy" can be used to determine how much confirmation the LLM will require.
"""

from .simple_tools_routes import SimpleToolsBackend
