from __future__ import annotations

import json
import logging

import requests

from ..services.file_utils import filename_from_url_and_type, register_bytes_as_uploaded_file
from ..services.file_analysis import (
    answer_from_files,
    find_relevant_files,
    get_file_keyword_catalog,
    generate_file_metadata,
)
from ..models import InternalTool, OpacaException
from .context import InternalToolContext


logger = logging.getLogger(__name__)


def _error_message(exc: Exception) -> str:
    if isinstance(exc, OpacaException) and exc.error_message:
        return f"{exc.user_message} {exc.error_message}"
    return str(exc) or type(exc).__name__


class FileTools:
    GROUP_NAME = "Files"

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
            InternalTool(
                name="FindRelevantFiles",
                description=(
                    "Select relevant uploaded files using filenames and keywords. Returns selected "
                    "file metadata and active status. Does not read full file contents or answer "
                    "content questions."
                ),
                params={"query": "string"},
                result="object",
                function=self.tool_find_relevant_files,
            ),
            InternalTool(
                name="GetFileKeywords",
                description=(
                    "List all uploaded files with filenames, keywords, active status, and whether "
                    "they are attached to the current message. Does not select files, read full "
                    "file contents, or call an LLM."
                ),
                params={},
                result="object",
                function=self.tool_get_file_keywords,
            ),
            InternalTool(
                name="SetActiveFiles",
                description=(
                    "Replace the current chat's active file working set after relevant file IDs are "
                    "known. Pass the complete set of file IDs that should be active, not only "
                    "newly relevant inactive files."
                ),
                params={"file_ids": "string"},
                result="object",
                function=self.tool_set_active_files,
            ),
            InternalTool(
                name="AskFiles",
                description=(
                    "Read active files and answer from their full contents. Use for questions, "
                    "summaries, overviews, or details that require actual file contents. "
                    "file_ids must be uploaded file IDs, not file names."
                ),
                params={
                    "question": "string",
                    "file_ids": "string",
                },
                result="object",
                function=self.tool_ask_files,
            ),
        ]

    def _active_file_ids(self) -> set[str]:
        if self.ctx.chat is None:
            return set(self.ctx.session.uploaded_files)
        return set(self.ctx.chat.active_files)

    def _parse_file_ids(self, file_ids: str | list[str] | None) -> set[str]:
        if file_ids is None:
            return set()
        if isinstance(file_ids, list):
            values = file_ids
        else:
            value = file_ids.strip()
            try:
                parsed = json.loads(value) if value.startswith("[") else None
            except json.JSONDecodeError:
                parsed = None
            values = parsed if isinstance(parsed, list) else value.split(",")

        return {str(file_id).strip() for file_id in values if str(file_id).strip()}

    def _selected_active_file_ids(
            self,
            file_ids: str | list[str],
    ) -> tuple[set[str], set[str]]:
        requested_ids = self._parse_file_ids(file_ids)
        return requested_ids & self._active_file_ids(), requested_ids

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

            file = await register_bytes_as_uploaded_file(
                session=self.ctx.session,
                content_type=content_type,
                filename=filename,
                data=resp.content,
            )
            if self.ctx.chat is not None:
                self.ctx.chat.active_files.add(file.file_id)
            await generate_file_metadata(
                self.ctx.session,
                file.file_id,
            )

            return {
                "ok": True,
                "file_id": file.file_id,
                "filename": filename,
                "keywords": file.keywords,
                "note": "File downloaded and made available for analysis.",
            }

        except Exception as e:
            logger.error(str(e))
            return {
                "ok": False,
                "error": str(e),
            }

    async def tool_find_relevant_files(self, query: str) -> dict:
        try:
            files = await find_relevant_files(
                self.ctx.session,
                query,
                current_file_ids=self.ctx.current_file_ids,
                active_file_ids=self._active_file_ids(),
                record_agent_message=self.ctx.record_agent_message,
            )
            inactive_file_ids = [
                file["file_id"]
                for file in files
                if not file["active"]
            ]
            return {
                "ok": True,
                "files": files,
                "inactive_file_ids": inactive_file_ids,
            }
        except Exception as exc:
            logger.exception("Finding relevant files failed")
            return {"ok": False, "files": [], "error": _error_message(exc)}

    async def tool_get_file_keywords(self) -> dict:
        files = get_file_keyword_catalog(
            self.ctx.session,
            current_file_ids=self.ctx.current_file_ids,
            active_file_ids=self._active_file_ids(),
        )
        inactive_file_ids = [
            file["file_id"]
            for file in files
            if not file["active"]
        ]
        return {
            "ok": True,
            "files": files,
            "inactive_file_ids": inactive_file_ids,
        }

    async def tool_set_active_files(self, file_ids: str | list[str]) -> dict:
        if self.ctx.chat is None:
            return {
                "ok": False,
                "error": "No chat is available for setting active files.",
            }

        selected_ids = self._parse_file_ids(file_ids) & set(self.ctx.session.uploaded_files)

        if not selected_ids:
            return {
                "ok": False,
                "files": [],
                "error": "No valid uploaded file IDs were provided. Active files were not changed.",
            }

        self.ctx.chat.active_files.clear()
        self.ctx.chat.active_files.update(selected_ids)

        active_files = [
            {
                "file_id": file_id,
                "file_name": file.file_name,
            }
            for file_id, file in self.ctx.session.uploaded_files.items()
            if file_id in selected_ids
        ]
        return {
            "ok": True,
            "files": active_files,
            "active_file_ids": sorted(selected_ids),
        }

    async def tool_ask_files(
            self,
            question: str,
            file_ids: str | list[str],
    ) -> dict:
        selected_ids, requested_ids = self._selected_active_file_ids(file_ids)
        if not selected_ids:
            return {
                "ok": False,
                "files": [],
                "unavailable_file_ids": sorted(requested_ids),
                "answer": "No valid active file IDs were provided.",
            }

        try:
            answer = await answer_from_files(
                self.ctx.session,
                question,
                selected_ids,
                record_agent_message=self.ctx.record_agent_message,
            )
        except Exception as exc:
            logger.exception("Answering from files failed")
            return {
                "ok": False,
                "files": [],
                "unavailable_file_ids": sorted(requested_ids - selected_ids),
                "error": _error_message(exc),
            }
        selected_files = [
            {
                "file_id": file_id,
                "file_name": file.file_name,
            }
            for file_id, file in self.ctx.session.uploaded_files.items()
            if file_id in selected_ids
        ]
        return {
            "ok": True,
            "files": selected_files,
            "unavailable_file_ids": sorted(requested_ids - selected_ids),
            "answer": answer,
        }
