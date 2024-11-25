"""
Simple approach, directly communicating with GPT/LLAMA (without LangChain), listing the
available actions in the system prompt (first message) along some explanation, and asking
the LLM in a loop until it thinks the user's request is fulfilled, parsing the LLM's
response for action invocations in JSON format and calling those along the way.
Works for both, GPT and LLAMA (but much better with GPT), and different models.
Parameter "ask_policy" can be used to determine how much confirmation the LLM will require.
"""

from .simple_routes import SimpleOpenAIBackend, SimpleLlamaBackend