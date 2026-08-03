import hashlib
import io
import re
import os
import tempfile
import logging
import shutil
from pathlib import Path
from urllib.parse import urlparse

import litellm
from fastapi import UploadFile
from starlette.datastructures import Headers

from .models import SessionData, OpacaFile, OpacaException, Chat

logger = logging.getLogger(__name__)


FILES_PATH = './data/files'


def _provider_file_key(session: SessionData, model: str, host: str, purpose: str) -> str:
    api_key = session.get_api_key(model)
    if not api_key:
        return f"{host}:{purpose}"

    fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return f"{host}:{purpose}:{fingerprint}"


def _file_upload_purpose(filename: str, host: str, model_supports_vision: bool) -> str | None:
    if is_image(filename) and model_supports_vision:
        return "vision"
    if is_pdf(filename):
        return "user_data" if host == "openai" else "assistants"
    return None


async def get_file_parts(session: SessionData, model: str, file_ids: list[str]):
    """Returns a list of file message parts for the given file-ids. Uploads all unsent files to the given model, if necessary."""

    host = model.rsplit("/", 1)[0]

    # Check if the selected host supports file upload
    if host not in ["openai", "azure", "vertex_ai", "bedrock"]:
        raise OpacaException(user_message=f"Host {host} does not support file upload.")

    # Check if model supports vision
    model_supports_vision = (bool(litellm.supports_vision(model=model)) and host == "openai")

    # Upload all files that haven't been uploaded to this host
    parts = []
    for file_id in file_ids:
        if file_id not in session.uploaded_files:
            raise OpacaException(user_message=f"File {file_id} not known in session.")
        file_data = session.uploaded_files[file_id]

        purpose = _file_upload_purpose(file_data.file_name, host, model_supports_vision)
        if not purpose:
            logger.info(f"Skipping file upload (Type not supported): {model} ({file_data.file_name})")
            continue

        provider_key = _provider_file_key(session, model, host, purpose)

        # If this provider/purpose/key combination does not already have an uploaded id, upload the file
        if provider_key not in file_data.host_ids:
            # prepare file for upload
            file_path = create_path(session.session_id, file_id)
            with open(file_path, 'rb') as f:
                file_obj = io.BytesIO(f.read())
                file_obj.name = file_data.file_name  # Required by OpenAI SDK

            # Upload to the current host and store host-specific id
            uploaded = await litellm.acreate_file(
                file=file_obj,
                purpose=purpose,
                custom_llm_provider=host,
                api_key=session.get_api_key(model),
            )
            logger.info(f"Uploaded file ID={uploaded.id} for file_id={file_id} (host={host})")
            # record host id under this host_url
            file_data.host_ids[provider_key] = uploaded.id

        # file uploaded -> create file message part        
        if is_image(file_data.file_name) and purpose == "vision":
            parts.append({"type": "input_image", "file_id": file_data.host_ids[provider_key]})
        else:
            parts.append({"type": "input_file", "file_id": file_data.host_ids[provider_key]})

    return parts


async def delete_file_from_all_clients(session: SessionData, file_id: str, ignore_error: bool) -> bool:
    """
    Delete a file (identified by file_id) from all LLM hosts
    it was uploaded to. Also removes it from session.uploaded_files.

    Args:
        session (SessionData): Current session containing uploaded_files and clients.
        file_id (str): The file identifier.
        ignore_error: Ignore all errors, always returns True
    """
    filedata = session.uploaded_files.get(file_id, None)
    if not filedata:
        return ignore_error

    for provider_key, host_file_id in filedata.host_ids.items():
        host = provider_key.split(":", maxsplit=1)[0]

        # Check if the selected host supports file deletion
        if not host in ["openai", "azure"]:
            logger.warning(f"Host {host} does not support file deletion.")
            continue

        try:
            await litellm.afile_delete(
                file_id=host_file_id,
                custom_llm_provider=host,
                api_key=session.get_api_key(f"{host}/dummy"),
            )
            logger.info(f"Deleted file {host_file_id} from host {host}")

        except Exception as e:
            logger.warning(f"Failed to delete file {host_file_id} from host {host}: {e}")
            # do not consider "not found" an error here
            if "404" not in str(e) and not ignore_error:
                return False

    # Remove from session after deletion attempts
    session.uploaded_files.pop(file_id, None)

    return True


async def save_file_to_disk(file: UploadFile, session: SessionData) -> OpacaFile:
    """
    Save an UploadFile to disk.
    """
    filename = file.filename

    # de-dupe by name
    for f in session.uploaded_files.values():
        if f.file_name == filename:
            return f

    file_data = OpacaFile(content_type=file.content_type, file_name=filename)
    file_path = create_path(session.session_id, file_data.file_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Add to uploaded_files
    session.uploaded_files[file_data.file_id] = file_data
    logger.info(f'Saving file to "{file_path}"')
    with open(file_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
    return file_data


def delete_file_from_disk(session_id: str, file_id: str) -> None:
    file_path = create_path(session_id, file_id)
    if file_path.is_file():
        logger.info(f'Deleting file {file_id} for session "{session_id}": {file_path}')
        file_path.unlink()


def delete_all_files_from_disk(session_id: str) -> None:
    dir_path = create_path(session_id)
    if dir_path.is_dir():
        logger.info(f'Deleting all files for session "{session_id}": {dir_path}')
        shutil.rmtree(dir_path)  # path.rmdir would require the dir to be empty first


def create_path(session_id: str, file_id: str = None) -> Path:
    if not file_id:
        return Path(FILES_PATH, session_id)
    return Path(FILES_PATH, session_id, file_id)


def rename_file(file: OpacaFile, new_name: str) -> None:
    file.file_name = f'{Path(file.file_name).with_stem(new_name)}'


def is_pdf(filename: str) -> bool:
    return bool(re.search(r"\.pdf$", filename or "", re.IGNORECASE))


def is_image(filename: str) -> bool:
    return bool(re.search(r"\.(png|jpe?g|gif|webp)$", filename or "", re.IGNORECASE))

EXT_BY_MIME = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

def filename_from_url_and_type(url: str, content_type: str | None) -> str:
    """
    Filename = last URL path segment + extension derived from content-type.
    No sanitization, deterministic.
    """
    parsed = urlparse(url)
    base = os.path.basename(parsed.path) or "file"

    # drop any existing extension
    if "." in base:
        base = base.rsplit(".", 1)[0]

    ct = (content_type or "").split(";", 1)[0].lower()
    ext = EXT_BY_MIME.get(ct, ".bin")

    return base + ext


async def register_bytes_as_uploaded_file(
        *,
        session: SessionData,
        content_type: str,
        filename: str,
        data: bytes,
) -> OpacaFile:
    """
    Registers raw bytes as an uploaded file in the current session,
    exactly like the /files route does.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()

        upload = UploadFile(
            filename=filename,
            file=open(tmp.name, "rb"),
            headers=Headers({"content-type": content_type})
        )

        filedata = await save_file_to_disk(upload, session)
        return filedata

    except Exception as e:
        logger.error(str(e))
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
