import io
import logging
import shutil
from pathlib import Path

import litellm
from fastapi import UploadFile
from .models import SessionData, OpacaFile

logger = logging.getLogger(__name__)


FILES_PATH = '/data/files'


async def upload_files(session: SessionData, host: str):
    """Uploads all unsent files to the connected LLM. Returns a list of file messages including file IDs."""

    # Upload all files that haven't been uploaded to this host
    for file_id, filedata in session.uploaded_files.items():
        # Skip suspended files
        if filedata.suspended:
            continue

        # Check if the selected host supports file upload
        if not host in ["openai", "azure", "vertex_ai", "bedrock"]:
            logger.warning(f"Host {host} does not support file upload.")
            break

        # If this host already has an uploaded id for this file, skip
        if host in filedata.host_ids:
            continue

        # prepare file for upload
        file_path = Path(FILES_PATH, session.session_id, filedata.file_id)
        with open(file_path, 'rb') as f:
            file_obj = io.BytesIO(f.read())
            file_obj.name = filedata.file_name  # Required by OpenAI SDK

        # Upload to the current host and store host-specific id
        uploaded = await litellm.acreate_file(file=file_obj, purpose="assistants", custom_llm_provider=host)
        logger.info(f"Uploaded file ID={uploaded.id} for file_id={file_id} (host={host})")
        # record host id under this host_url
        filedata.host_ids[host] = uploaded.id

    return [
        {"type": "input_file", "file_id": filedata.host_ids[host]}
        for filedata in session.uploaded_files.values()
        if (not filedata.suspended) and (host in filedata.host_ids)
    ]


async def delete_file_from_all_clients(session: SessionData, file_id: str) -> bool:
    """
    Delete a file (identified by file_id) from all LLM hosts
    it was uploaded to. Also removes it from session.uploaded_files.

    Args:
        session (SessionData): Current session containing uploaded_files and clients.
        file_id (str): The file identifier.
    """
    filedata = session.uploaded_files.get(file_id, None)
    if not filedata:
        return False

    for host, host_file_id in filedata.host_ids.items():
        # Check if the selected host supports file deletion
        if not host in ["openai", "azure"]:
            logger.warning(f"Host {host} does not support file deletion.")
            continue

        try:
            # Assume the provider to be openai for now
            await litellm.afile_delete(file_id=host_file_id, custom_llm_provider=host)
            logger.info(f"Deleted file {host_file_id} from host {host}")

        except Exception as e:
            logger.warning(
                f"Failed to delete file {host_file_id} from host {host}: {e}"
            )
            return False

    # Remove from session after deletion attempts
    session.uploaded_files.pop(file_id, None)

    return True


async def save_file_to_disk(file: UploadFile, session_id: str) -> OpacaFile:
    """
    Save an UploadFile to disk.
    """
    file_data = OpacaFile(content_type=file.content_type, file_name=file.filename)
    file_path = Path(FILES_PATH, session_id, file_data.file_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f'Saving file to "{file_path}"')
    with open(file_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
    return file_data


def delete_files_for_session(session_id: str) -> None:
    dir_path = Path(FILES_PATH, session_id)
    if dir_path.is_dir():
        logger.info(f'Deleting files for session "{session_id}": {dir_path}')
        shutil.rmtree(dir_path)
