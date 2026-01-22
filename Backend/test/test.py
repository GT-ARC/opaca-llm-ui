"""
The purpose of these tests is NOT to measure how fast or overall "good" the LLM
is. That's what the Benchmarks are for. These tests are much more simple: Just
to see whether it all works. Whether tools are called (any tools, really),
whether the LLM has access to the message history, whether there are any other
unexpected errors, and whether all the other non-LLM routes work.

How to test:
- start SAGE Backend, either via Docker Compose or directly
- run as "pytest test.py -v" or "pytest test.py -v --durations=0" for a mini-benchmark
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

# create test client
client = BackendTestClient("http://localhost:3001")
if not client.alive():
    print("Make sure SAGE Backend is running!")
    exit(1)

# reset sessions and message histories
client.delete_chats()


# TODO find some faster test query for the LLM? find-temp takes too long...
#  maybe something with just one tool call (just get the sensor ID?)
#  but at the same time it would also be good to test execution more iters.


# TEST GENERAL STUFF (could also be part of the setup...)

def test_connect():
    ip = os.getenv("VITE_PLATFORM_BASE_URL")
    print("IP FROM ENV:", ip)
    res = client.connect(ip)
    assert res == 200, "Failed to connect; OPACA RP not running?"


# TEST LLM METHODS, TOOL-CALLING, HISTORY, ...

def test_simple():
    ask_sample_question("simple")


def test_simple_followup():
    ask_follow_up_question("simple")


def test_simple_tools():
    ask_sample_question("simple-tools")


def test_simple_tools_followup():
    ask_follow_up_question("simple-tools")


def test_tool_llm():
    ask_sample_question("tool-llm")


def test_tool_llm_followup():
    ask_follow_up_question("tool-llm")


def test_self_orchestrated():
    ask_sample_question("self-orchestrated")


def test_self_orchestrated_followup():
    ask_follow_up_question("self-orchestrated")


# TEST GENERAL STUFF

NUM_CHATS = 4
def test_chat_histories():
    chats = client.get_chats()
    assert len(chats) == NUM_CHATS

    chat_histories = [client.get_chat_history(chat["chat_id"]) for chat in chats]
    print(chat_histories)
    assert all(len(chat["responses"]) == 2 for chat in chat_histories)

    res = client.delete_chat("does-not-exist")
    assert res == False

    res = client.delete_chat(chats[0]["chat_id"])
    assert res == True

    chats = client.get_chats()
    assert len(chats) == NUM_CHATS - 1


def test_config():
    conf = client.get_config("simple")
    conf["config_values"]["temperature"] = 1.5

    client.set_config("simple", conf["config_values"])
    conf = client.get_config("simple")
    assert conf["config_values"]["temperature"] == 1.5

    client.reset_config("simple")
    conf = client.get_config("simple")
    assert conf["config_values"]["temperature"] == 1.0


# HELPER METHODS

def ask_sample_question(method):
    """ask question that should execute a tool call"""
    run_test_queries(method, "What is the temperature in the conference room?")


def ask_follow_up_question(method):
    """ask question that requires context from previous question (test history)"""
    run_test_queries(method, "And in the kitchen?")


def run_test_queries(method, *queries):
    """test whether each query produces at least one tool call and no errors"""
    chat_id = f"chat-{method}"
    for query in queries:
        res = client.query_chat(method, chat_id, query)
        print("RESULT", res)
        assert not res.get("error"), f"There was an error with query '{query}'."
        assert any(m["tools"] for m in res.get("agent_messages", [])), f"Query '{query}' did not trigger a tool call."
