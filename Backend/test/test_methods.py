"""
The purpose of these tests is NOT to measure how fast or overall "good" the LLM
is. That's what the Benchmarks are for. These tests are much more simple: Just
to see whether it all works. Whether tools are called (any tools, really),
whether the LLM has access to the message history, whether there are any other
unexpected errors, and whether all the other non-LLM routes work.

How to test:
- start OPACA Runtime Platform (RP)
- Deploy the Smart office container to it (rkader2811/smart-office)
- set the environment variable VITE_PLATFORM_BASE_URL to the URL of the RP
- run "python -m test" from /Backend to run all tests

Note:
- all method or classes that start with "test" are considered tests
- tests are executed in order and may depend on each others
- subsequent tests are executed even if earlier tests failed
- print is only shown on failed tests
- if the URL is not set, the tests are skipped
"""

import os
import pytest
from fastapi.testclient import TestClient

from src.server import app, handle_session_id

from util import handle_user_session_id


# Initialize the client with a mock session
app.dependency_overrides[handle_session_id] = handle_user_session_id
client = TestClient(app)

# Define methods to parameterize tests
methods = ["simple", "simple-tools", "tool-llm", "self-orchestrated"]

# Get the OPACA RP URL from the environment variable
URL = os.getenv("VITE_PLATFORM_BASE_URL")


# TODO find some faster test query for the LLM? find-temp takes too long...
#  maybe something with just one tool call (just get the sensor ID?)
#  but at the same time it would also be good to test execution more iters.


# TEST GENERAL STUFF (could also be part of the setup...)

@pytest.mark.skipif(not URL, reason="OPACA RP URL not set in environment")
def test_connect():
    print("URL FROM ENV:", URL)
    res = client.post("/connect", json={"url": URL, "user": None, "pwd": None})
    assert res.status_code == 200, "Failed to connect; OPACA RP not running?"


# TEST LLM METHODS, TOOL-CALLING, HISTORY, ...

@pytest.mark.parametrize("method", methods)
@pytest.mark.skipif(not URL, reason="OPACA RP URL not set in environment")
def test_sample_question(method):
    run_test_queries(method, "What is the temperature in the conference room?")

@pytest.mark.parametrize("method", methods)
@pytest.mark.skipif(not URL, reason="OPACA RP URL not set in environment")
def test_simple_followup(method):
    run_test_queries(method, "And in the kitchen?")


# TEST GENERAL STUFF

NUM_CHATS = 4
@pytest.mark.skipif(not URL, reason="OPACA RP URL not set in environment")
def test_chat_histories():
    chats = client.get("/chats").json()
    assert len(chats) == NUM_CHATS

    chat_histories = [client.get(f"/chats/{chat['chat_id']}").json() for chat in chats]
    print(chat_histories)
    assert all(len(chat["responses"]) == 2 for chat in chat_histories)

    res = client.delete("/chats/does-not-exist")
    assert res.json() == False

    res = client.delete(f"/chats/{chats[0]['chat_id']}")
    assert res.json() == True

    chats = client.get("/chats").json()
    assert len(chats) == NUM_CHATS - 1


# HELPER METHODS

def run_test_queries(method, *queries):
    """test whether each query produces at least one tool call and no errors"""
    chat_id = f"chat-{method}"
    for query in queries:
        res = client.post(f"/chats/{chat_id}/query/{method}", json={"user_query": query})
        print("RESULT", res)
        assert not res.is_error, f"There was an error with query '{query}'."
        assert any(m["tools"] for m in res.json().get("agent_messages", [])), f"Query '{query}' did not trigger a tool call."
