"""
How to test:
- start OPACA LLM Backend, either via Docker Compose or directly
- run as "pytest test.py -v"
- run "pytest test.py::<name>" to run a single test

Note:
- all method or classes that start with "test" are considered tests
- tests are executed in order and may depend on each others
- subsequent tests are executed even if earlier tests failed
- print is only shown on failed tests
"""

import os
from util import BackendTestClient

# SETUP

client = BackendTestClient("http://localhost:3001")
if not client.alive():
    print("Make sure OPACA LLM Backend is running!")
    exit(1)

"""
test-query each model
with and without history
get chats, delete chat, get chat
get history
change config, get config, reset config
"""

# TESTS

def test_connect():
    ip = os.getenv("VITE_PLATFORM_BASE_URL")
    print("IP FROM ENV:", ip)
    res = client.connect(ip)
    assert res == 200, "Failed to connect; OPACA RP not running?"

def test_simple():
    run_test_queries("simple")

def test_simple_tools():
    run_test_queries("simple-tools")

def test_tool_llm():
    run_test_queries("tool-llm")

def test_self_orchestrated():
    run_test_queries("self-orchestrated")


# HELPER METHODS

def run_test_queries(method):
    chat_id = f"chat-{method}"
    queries = [
        "What is the CO2 in the Co-Working space?",
        "And in the kitchen?",
    ]
    for query in queries:
        res = client.query_chat(method, chat_id, query)
        print("RESULT", res)
        assert not res.get("error"), f"There was an error with query {query}."
        assert any(m["tools"] for m in res.get("agent_messages", [])), f"Query {query} did not trigger a tool call."
