from fastapi.testclient import TestClient

from src.models import SessionData
from src.server import app, handle_session_id

prompt_session = SessionData(_id="1234-test")

app.dependency_overrides[handle_session_id] = prompt_session

client = TestClient(app)

def test_get_prompts():
    res = client.get("/prompts")
    assert res.status_code == 200

def test_set_prompts():
    res = client.post(
        "/prompts",
        json={
            "GB": [
                {
                    "id": "testSection",
                    "header": "TestSection",
                    "icon": "🤖",
                    "visible": False,
                    "questions": [
                        {
                            "question": "This is a test question",
                            "icon": "🔧"
                        }
                    ]
                }
            ]
        })
    assert res.status_code == 200

    res = client.get("/prompts")
    prompts = res.json()["GB"]
    print(prompts)
    assert any(q["id"] == "testSection" and q["questions"][0]["question"] == "This is a test question" for q in prompts)

def test_delete_prompts():
    res = client.delete("/prompts")
    assert res.status_code == 200

    res = client.get("/prompts")
    prompts = res.json()["GB"]
    assert all(q["id"] != "testSection" and q["questions"][0]["question"] != "This is a test question" for q in prompts)

def test_get_prompts_default():
    res = client.get("/prompts/default")
    assert res.status_code == 200

def test_set_prompts_default():
    res = client.post(
        "/prompts/default",
        json={
            "GB": [
                {
                    "id": "testSection",
                    "header": "TestSection",
                    "icon": "🤖",
                    "visible": False,
                    "questions": [
                        {
                            "question": "This is a test question",
                            "icon": "🔧"
                        }
                    ]
                }
            ]
        })
    assert res.status_code == 200

    res = client.get("/prompts/default")
    assert res.json()["GB"][0]["questions"][0]["question"] == "This is a test question"

def test_reset_prompts_default():
    res = client.delete("/prompts/default")
    assert res.status_code == 200

    res = client.get("/prompts/default")
    prompts = res.json()["GB"]
    assert all(q["id"] != "testSection" and q["questions"][0]["question"] != "This is a test question" for q in prompts)
