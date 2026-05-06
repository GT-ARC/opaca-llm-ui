from __future__ import annotations

import logging

import requests

from ..file_utils import filename_from_url_and_type, register_bytes_as_uploaded_file
from .context import InternalToolContext
from .definitions import InternalTool


logger = logging.getLogger(__name__)


class FileTools:
    def __init__(self, ctx: InternalToolContext):
        self.ctx = ctx

    def tools(self) -> list[InternalTool]:
        return [
            InternalTool(
                name="ReadFileFromUrl",
                description="Downloads a file from a URL and uploads it to the backend to be used by the LLM.",
                params={"url": "string"},
                result="object",
                function=self.tool_read_file_from_url,
            ),
        ]

    async def tool_read_file_from_url(self, url: str) -> dict:
        try:
            resp = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()

            content_type = resp.headers.get("Content-Type")
            filename = filename_from_url_and_type(url, content_type)

            await register_bytes_as_uploaded_file(
                session=self.ctx.session,
                content_type=content_type,
                filename=filename,
                data=resp.content,
            )

            return {
                "ok": True,
                "filename": filename,
                "note": "File downloaded and made available for analysis.",
            }

        except Exception as e:
            logger.error(str(e))
            return {
                "ok": False,
                "error": str(e),
            }
