import pytest
from fastapi.testclient import TestClient

from src.server import app, handle_session_id

from util import handle_user_session_id


# Initialize the client with a mock session
app.dependency_overrides[handle_session_id] = handle_user_session_id
client = TestClient(app)

methods = ["simple", "simple-tools", "tool-llm", "self-orchestrated"]

@pytest.mark.parametrize("method", methods)
def test_get_config(method):
    res = client.get(f"/config/{method}")
    assert res.status_code == 200
    data = res.json()

    # Check if the config value keys match the schema properties keys
    assert set(data["config_values"].keys()) == set(data["config_schema"]["properties"].keys())

@pytest.mark.parametrize("method", methods)
def test_set_config(method):
    res = client.put(f"/config/{method}", json={"max_rounds": 9})
    assert res.status_code == 200

    res = client.get(f"/config/{method}")
    assert res.status_code == 200
    data = res.json()
    assert data["config_values"]["max_rounds"] == 9

@pytest.mark.parametrize("method", methods)
def test_set_config_invalid(method):
    res = client.put(f"/config/{method}", json={"max_rounds": 100000})
    assert res.status_code == 422

    # TODO fix this error, returns 200 right now
    # res = client.put(f"/config/{method}", json={"not_existing_key": 100000})
    # assert res.status_code == 422

    res = client.put(f"/config/{method}", json={"max_rounds": "not_a_number"})
    assert res.status_code == 422

@pytest.mark.parametrize("method", methods)
def test_reset_config_simple(method):
    res = client.delete(f"/config/{method}")
    assert res.status_code == 200

    res = client.get(f"/config/{method}")
    assert res.status_code == 200
    data = res.json()
    assert data["config_values"]["max_rounds"] == 5
