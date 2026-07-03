from __future__ import annotations

from textwrap import dedent

from ..models import InternalTool, PlayBook
from .context import InternalToolContext


class PlayBookTools:
    GROUP_NAME = "PlayBooks"

    def __init__(self, ctx: InternalToolContext):
        self.ctx = ctx

    def tools(self) -> list[InternalTool]:
        tools = [
            InternalTool(
                name="CreatePlayBook",
                description=(
                    "Create and enable a reusable play book for future user requests. "
                    "Use this when the user explicitly asks to define, remember, or save reusable behavior. "
                    "Describe when the play book should be loaded and the detailed instructions to follow. "
                    "Do not create a play book merely to fulfill a one-time request."
                ),
                params={
                    "name": "string",
                    "when_to_use": "string",
                    "what_to_do": "string",
                },
                result="object",
                function=self.tool_create_play_book,
            ),
        ]

        if self._enabled_play_books():
            tools.insert(
                0,
                InternalTool(
                    name="LoadPlayBook",
                    description=self._loader_description(),
                    params={"play_book_id": "string"},
                    result="string",
                    function=self.tool_load_play_book,
                ),
            )

        return tools

    def _enabled_play_books(self) -> list[PlayBook]:
        return self.ctx.session.enabled_play_books()

    def _loader_description(self) -> str:
        play_book_lines = []
        for play_book in self._enabled_play_books():
            play_book_lines.append(
                f"- play_book_id: {play_book.id}\n"
                f"  Name: {play_book.name}\n"
                f"  When to use: {play_book.when_to_use}"
            )
        play_books_text = "\n".join(play_book_lines)

        return dedent(f"""
            Load detailed instructions for a user-defined play book.

            Call this tool before answering when the user's request clearly matches one of the available play books.
            Do not call this tool if none of the play books are relevant.

            Available play books:
            {play_books_text}

            Pass the exact play_book_id of the matching play book.
        """).strip()

    async def tool_create_play_book(self, name: str, when_to_use: str, what_to_do: str) -> dict:
        values = {
            "name": name.strip(),
            "when_to_use": when_to_use.strip(),
            "what_to_do": what_to_do.strip(),
        }
        if not all(values.values()):
            raise ValueError("Play book name, usage description, and instructions must not be empty.")

        play_book = PlayBook(
            **values,
        )
        self.ctx.session.set_play_book(play_book)
        return {
            "created": True,
            "play_book": play_book.model_dump(),
        }

    async def tool_load_play_book(self, play_book_id: str) -> str:
        play_book = next((item for item in self._enabled_play_books() if item.id == play_book_id), None)
        if play_book is None:
            available = ", ".join(item.id for item in self._enabled_play_books()) or "none"
            return (
                f"No enabled play book with play_book_id '{play_book_id}' was found. "
                f"Available play book IDs: {available}."
            )

        return dedent(f"""
            Play book loaded: {play_book.name}

            Follow these user-defined instructions for the current request:
            {play_book.what_to_do}
        """).strip()
