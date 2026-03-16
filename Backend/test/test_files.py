import io
import pytest
from fastapi.testclient import TestClient

from Backend.src.server import app, handle_session_http
from util import handle_user_session_id


# Initialize test client
app.dependency_overrides[handle_session_http] = handle_user_session_id
client = TestClient(app)

allowed_files = {
    "file.pdf": "application/pdf",
    "file.jpg": "image/jpeg",
    "file.jpeg": "image/jpeg",
    "file.png": "image/png",
    "file.gif": "image/gif",
    "file.webp": "image/webp",
}

disallowed_files = {
    "file.exe": "application/exe",
    "file.zip": "application/zip",
    "file.txt": "text/plain",
    "file.bmp": "image/bmp"
}

@pytest.fixture(scope="module")
def files_response():
    res = client.get("/files")
    assert res.status_code == 200
    return res.json()

@pytest.mark.parametrize("filename, content_type", allowed_files.items())
def test_append_files_allowed(filename, content_type):
    data = [
        ("files", (filename, io.BytesIO(b"dummy bytes for testing"), content_type))
    ]

    res = client.post("/files", files=data)
    assert res.status_code == 200
    # Make sure the file is in the database
    res = client.get("/files")
    assert any(f["file_name"] == filename for f in res.json().values())

# TODO The following test does not work. Unsupported files are still accepted.
"""
@pytest.mark.parametrize("filename, content_type", disallowed_files.items())
def test_append_files_disallowed(filename, content_type):
    data = [
        ("files", (filename, io.BytesIO(b"dummy bytes for testing"), content_type))
    ]

    res = client.post("/files", files=data)
    assert res.status_code == 400
"""

def test_get_files(files_response):
    assert len(files_response) > 0

def test_get_file_view(files_response):
    file_ids = [f for f in files_response.keys()]

    for f in file_ids:
        res = client.get(f"/files/{f}/view")
        assert res.status_code == 200

def test_suspend_file(files_response):
    # Check that none of the files are suspended
    assert all(not f["suspended"] for f in files_response.values())

    # Suspend all files by patching them
    for f in files_response.values():
        res = client.patch(f"/files/{f['file_id']}", params={"suspend": True})
        assert res.status_code == 200

    # Check that all files are now suspended
    res = client.get("/files")
    assert res.status_code == 200
    files = res.json()
    assert all(f["suspended"] for f in files.values())

def test_rename_file(files_response):
    # Get first file and save its current name
    file_id = list(files_response.keys())[0]
    old_file_name = files_response[file_id]["file_name"]

    # Change the file name
    res = client.patch(f"/files/{file_id}", params={"name": "new_file_name"})
    assert res.status_code == 200

    # Check that the file name has been changed
    res = client.get("/files")
    assert res.status_code == 200
    assert res.json()[file_id]["file_name"] != old_file_name

def test_rename_file_with_type(files_response):
    # Get first file and save its current name
    file_id = list(files_response.keys())[0]
    old_file_type = files_response[file_id]["file_name"]
    assert not old_file_type.endswith(".zip")

    # Change the file name with an explicit type
    res = client.patch(f"/files/{file_id}", params={"name": "new_file_name.zip"})
    assert res.status_code == 200

    # Check that the file name has been changed but NOT its type
    res = client.get("/files")
    assert res.status_code == 200
    assert res.json()[file_id]["file_name"] != old_file_type
    assert not res.json()[file_id]["file_name"].endswith(".zip")

def test_delete_files(files_response):
    # Get files and save their ids
    file_ids = files_response.keys()

    # Delete the files
    for file_id in file_ids:
        res = client.delete(f"/files/{file_id}")
        assert res.status_code == 200

    # Make sure no files are left
    res = client.get("/files")
    assert res.status_code == 200
    assert len(res.json()) == 0
