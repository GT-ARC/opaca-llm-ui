import io
import os
import logging
from openai import AsyncOpenAI
from .models import SessionData
from .utils import get_supported_models

logger = logging.getLogger(__name__)


async def upload_files(host_url: str, session: SessionData, client: AsyncOpenAI):
    """Uploads all unsent files to the connected LLM. Returns a list of file messages including file IDs."""

    # Upload all files that haven't been uploaded to this host
    for file_id, filedata in session.uploaded_files.items():
        # Skip suspended files
        if filedata.suspended:
            continue

        # If this host already has an uploaded id for this file, skip
        if host_url in filedata.host_ids:
            continue

        # prepare file for upload
        file_bytes = filedata._content.getvalue()  # Access private content
        file_obj = io.BytesIO(file_bytes)
        file_obj.name = filedata.file_name  # Required by OpenAI SDK

        # Upload to the current host and store host-specific id
        uploaded = await client.files.create(file=file_obj, purpose="user_data")
        logger.info(f"Uploaded file ID={uploaded.id} for file_id={file_id} (host={host_url})")
        # record host id under this host_url
        filedata.host_ids[host_url] = uploaded.id

    return [
        {"type": "input_file", "file_id": filedata.host_ids[host_url]}
        for filedata in session.uploaded_files.values()
        if (not filedata.suspended) and (host_url in filedata.host_ids)
    ]


async def delete_file_from_all_clients(session: SessionData, file_id: str) -> bool:
    """
    Delete a file (identified by file_id) from all LLM hosts
    it was uploaded to. Also removes it from session.uploaded_files.

    Args:
        session (SessionData): Current session containing uploaded_files and clients.
        file_id (str): The file identifier.
    """
    filedata = session.uploaded_files.get(file_id)
    if not filedata:
        return False

    for host_url, host_file_id in filedata.host_ids.items():
        try:
            # Reuse or create a client for this host
            if host_url not in session.llm_clients:
                for url, key, _ in get_supported_models():
                    if url == host_url:
                        session.llm_clients[url] = (
                            AsyncOpenAI(api_key=key if key else os.getenv("OPENAI_API_KEY"))
                            if url == "openai"
                            else AsyncOpenAI(api_key=key, base_url=url)
                        )
                        break

            client = session.llm_clients[host_url]
            await client.files.delete(host_file_id)
            logger.info(f"Deleted file {host_file_id} from host {host_url}")

        except Exception as e:
            logger.warning(
                f"Failed to delete file {host_file_id} from host {host_url}: {e}"
            )
            return False

    # Remove from session after deletion attempts
    session.uploaded_files.pop(file_id, None)

    return True