from fastapi.testclient import TestClient

from Backend.src.server import app, handle_session_http
from util import handle_user_session_id

app.dependency_overrides[handle_session_http] = handle_user_session_id
client = TestClient(app)

def test_add_mcp():
    mcp_content = {
        "type": "mcp",
        "server_url": "https://mcp.deepwiki.com/mcp",
        "server_label": "DeepWiki",
        "require_approval": "never"
    }
    res = client.post("/mcp", json={"content": mcp_content})
    assert res.status_code == 201

def test_get_mcp():
    res = client.get("/mcp")
    assert res.status_code == 200
    assert "DeepWiki" in res.json().keys()

def test_add_mcp_invalid_url():
    mcp_content = {
        "type": "mcp",
        "server_url": "https://example.com",
        "server_label": "DeepWiki",
        "require_approval": "never"
    }
    res = client.post("/mcp", json={"content": mcp_content})
    assert res.status_code == 400

def test_add_mcp_duplicate():
    mcp_content = {
        "type": "mcp",
        "server_url": "https://mcp.deepwiki.com/mcp",
        "server_label": "DeepWiki",
        "require_approval": "never"
    }
    res = client.post("/mcp", json={"content": mcp_content})
    assert res.status_code == 400

def test_delete_mcp():
    res = client.delete("/mcp/DeepWiki")
    assert res.status_code == 204

def test_delete_mcp_invalid():
    res = client.delete("/mcp/ExampleMCP")
    assert res.status_code == 404

def test_add_mcp_without_server_label():
    mcp_content = {
        "type": "mcp",
        "server_url": "https://mcp.deepwiki.com/mcp",
        "server_label": "",
        "require_approval": "never"
    }
    res = client.post("/mcp", json={"content": mcp_content})
    assert res.status_code == 201

    res = client.get("/mcp")
    # The server should automatically resolve the mcp name
    assert "mcp-deepwiki-com" in res.json().keys()
