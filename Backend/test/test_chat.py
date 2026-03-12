import threading
import time
import uuid

import litellm
import pytest
from fastapi.testclient import TestClient

from src.models import SessionData
from src.server import app, handle_session_id
from util import handle_user_session_id

# Use mock completion from litellm
litellm.mock_completion = True

app.dependency_overrides[handle_session_id] = handle_user_session_id

client = TestClient(app)

methods = ["simple", "simple-tools", "tool-llm", "self-orchestrated"]

chats = {}


@pytest.mark.parametrize("method", methods)
def test_query(method):
    """Test the /query endpoint"""
    res = client.post(f"/query/{method}", json={"user_query": "Hello"})

    assert res.status_code == 200

@pytest.mark.parametrize("method", methods)
def test_chat_query(method):
    """Test the /chats endpoint with a mock LLM response."""
    chats[method] = uuid.uuid4()
    res = client.post(f"/chats/{chats[method]}/query/{method}", json={"user_query": "Hello"})

    assert res.status_code == 200

@pytest.mark.parametrize("method", methods)
def test_get_chat_by_id(method):
    """Test if the previously created chats can be queried."""
    res = client.get(f"/chats/{chats[method]}")
    assert res.status_code == 200

def test_get_non_existing_chat():
    """Test if a non-existing chat returns a 404."""
    res = client.get("/chats/abcd")
    assert res.status_code == 404

@pytest.mark.parametrize("method", methods)
def test_stop_query(method):
    """Test the /stop endpoint. Requires an open websocket connection."""
    with client.websocket_connect("/ws"):

        def run_query():
            res = client.post(f"/chats/{chats[method]}/query/{method}", json={"user_query": "Hello", "streaming": True})
            assert res.status_code == 200
            assert "stopped" in res.json()["content"]

        # Start the query in another thread
        query_thread = threading.Thread(target=run_query)
        query_thread.start()

        # Wait for the query to start
        time.sleep(0.1)

        # Send the stop request
        stop_res = client.post("/stop")
        assert stop_res.status_code == 200

        query_thread.join()

def test_append_push_message():
    """Append another message to a chat"""
    res = client.post(
        f"/chats/{chats.get('simple')}/append",
        params={"auto_append": False},
        json={
            "query": "Test Append",
            "agent_messages": [],
            "iterations": 0,
            "execution_time": 0,
            "content": "validate_append",
            "error": "",
            "task_id": 0
        }
    )
    assert res.status_code == 200

    res = client.get(f"/chats/{chats.get('simple')}")
    assert res.status_code == 200
    assert res.json().get("responses")[-1].get("content") == "validate_append"

def test_update_chat_name():
    """Update the name of a chat"""
    # Get the current name of the chat
    res = client.get(f"/chats/{chats.get('simple')}")
    assert res.status_code == 200
    assert res.json().get("name") != "validate_name_change"

    # Change the name of the chat
    res = client.put(f"/chats/{chats.get('simple')}", params={"new_name": "validate_name_change"})
    assert res.status_code == 200

    # Confirm that the new name has been set
    res = client.get(f"/chats/{chats.get('simple')}")
    assert res.status_code == 200
    assert res.json().get("name") == "validate_name_change"

def test_delete_single_chat():
    """Delete a single chat"""
    # Confirm that the chat exists and is not empty
    res = client.get(f"/chats/{chats.get('simple')}")
    assert res.status_code == 200
    assert len(res.json().get("responses")) != 0

    # Delete the chat
    res = client.delete(f"/chats/{chats.get('simple')}")
    assert res.status_code == 200

    # Confirm that the chat is now empty
    res = client.get(f"/chats/{chats.get('simple')}")
    assert res.status_code == 404

def test_delete_all_chats():
    # Confirm that any chat still has messages
    res = client.get("/chats")
    assert res.status_code == 200
    assert len(res.content) != 0

    # Delete all chats
    res = client.delete("/chats")
    assert res.status_code == 200

    # Confirm that all chats are now empty
    res = client.get("/chats")
    assert len(res.json()) == 0

