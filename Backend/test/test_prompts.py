from fastapi.testclient import TestClient

from src.server import app, handle_session_id
from util import example_prompt, handle_user_session_id


# Initialize the client with a mock session
app.dependency_overrides[handle_session_id] = handle_user_session_id
client = TestClient(app)


def test_get_prompts():
    res = client.get("/prompts")
    assert res.status_code == 200

def test_set_prompts():
    res = client.post(
        "/prompts",
        json=example_prompt())
    assert res.status_code == 200

    res = client.get("/prompts")
    prompts = res.json()["GB"]
    # Check if the prompt in "example_prompt()" is found in any of the retrieved prompts
    assert any(q["id"] == "testSection" and q["questions"][0]["question"] == "This is a test question" for q in prompts)

def test_delete_prompts():
    res = client.delete("/prompts")
    assert res.status_code == 200

    res = client.get("/prompts")
    prompts = res.json()["GB"]
    assert all(q["id"] != "testSection" and q["questions"][0]["question"] != "This is a test question" for q in prompts)
