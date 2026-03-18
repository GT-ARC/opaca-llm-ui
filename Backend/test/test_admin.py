"""
To test the admin actions, we define two clients.
One for the user, and another one for the admin.
"""
from unittest.mock import patch, AsyncMock
import os

import pytest
from fastapi.testclient import TestClient

from Backend.src.models import ScheduledTask
from Backend.src.session_manager import create_or_refresh_session
from Backend.src.server import app, handle_session_http

from util import example_prompt, handle_admin_session_id, handle_user_session_id

# Set the admin password
ADMIN_PWD = "test-admin"
os.environ["SESSION_ADMIN_PWD"] = ADMIN_PWD


# Initialize two clients, one for the user, and another one for the admin
app.dependency_overrides[handle_session_http] = handle_admin_session_id
client = TestClient(app)

app.dependency_overrides[handle_session_http] = handle_user_session_id
user_client = TestClient(app)


def test_initialize_session_with_chat():
    res = user_client.post(
        "/chats/example-chat-id/append",
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

def test_no_admin_password():
    res = client.get("/admin/sessions")
    assert res.status_code == 401

def test_get_sessions():
    res = client.get("/admin/sessions", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_set_default_prompts():
    # Get the current default prompts
    res = client.get("/prompts/default")
    assert res.status_code == 200
    default_prompts = res.json()

    # Set new default prompts
    res = client.post("/prompts/default", json=example_prompt(), headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200

    # Validate that the prompts have changed
    res = client.get("/prompts/default")
    assert res.status_code == 200
    assert res.json() != default_prompts

def test_reset_default_prompts():
    # Get the just changed default prompts
    res = client.get("/prompts/default")
    assert res.status_code == 200
    default_prompts = res.json()

    # Reset the default prompts
    res = client.delete("/prompts/default", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200

    # Validate that the prompts have been reset
    res = client.get("/prompts/default")
    assert res.status_code == 200
    assert res.json() != default_prompts

def test_restrict_tool():
    res = client.put("/admin/restrict", json={"forbidden": ["tool_FBD"], "need_confirmation": ["tool_NC"]}, headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200

    res = client.get("/admin/restrict")
    assert res.status_code == 200
    assert res.json() == {"forbidden": ["tool_FBD"], "need_confirmation": ["tool_NC"]}

# SESSION ADMIN UPDATE
@pytest.mark.anyio
async def test_stop_scheduled_task():
    # Get the user session directly
    user_session = await create_or_refresh_session("user")

    # Sanity check what sessions exist
    res = client.get("/admin/sessions", headers={"x-api-password": ADMIN_PWD})
    assert user_session.session_id in res.json().keys()

    user_session.scheduled_tasks = {0: ScheduledTask(method="simple", task_id=0, query="test", next_time="never", interval=0, repetitions=-1)}
    res = client.put(f"/admin/sessions/{user_session.session_id}/STOP_TASKS", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert user_session.scheduled_tasks == {}

@pytest.mark.anyio
async def test_block_session():
    # Get the user session directly
    user_session = await create_or_refresh_session("user")

    # Block the user
    res = client.put(f"/admin/sessions/{user_session.session_id}/BLOCK", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert user_session.blocked == True

    # Make sure the user is blocked
    res = user_client.get("/chats")
    assert res.status_code == 400

    # Unblock the user
    res = client.put(f"/admin/sessions/{user_session.session_id}/UNBLOCK", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert user_session.blocked == False

    # Make sure the user is unblocked
    res = user_client.get("/chats")
    assert res.status_code == 200

# The LOGOUT action internally calls the POST /containers/{id}/logout route
# We mock this response by returning a 200 status code
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
@pytest.mark.anyio
async def test_logout_session(mock_post):
    # Mock the logout call to the OPACA platform
    mock_post.return_value.status_code = 200

    # Get the user session directly
    user_session = await create_or_refresh_session("user")

    # Modify the container login list manually
    user_session.opaca_client.logged_in_containers["example-container"] = "TestToken"

    # Make sure the container login is present
    res = client.get("/admin/sessions", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert len(res.json()[user_session.session_id]["container-logins"]) > 0

    # Logout the user session
    res = client.put(f"/admin/sessions/{user_session.session_id}/LOGOUT", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200

    # Make sure the container login is no longer present
    res = client.get("/admin/sessions", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert len(res.json()[user_session.session_id]["container-logins"]) == 0

@pytest.mark.anyio
async def test_delete_session():
    # Get the user session directly
    user_session = await create_or_refresh_session("user")

    # Delete the user session
    res = client.put(f"/admin/sessions/{user_session.session_id}/DELETE", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200

    # Make sure the user session is no longer present
    res = client.get("/admin/sessions", headers={"x-api-password": ADMIN_PWD})
    assert res.status_code == 200
    assert user_session.session_id not in res.json().keys()
