from __future__ import annotations

import json
from textwrap import dedent

from .context import InternalToolContext
from .definitions import InternalTool


class ChatTools:
    def __init__(self, ctx: InternalToolContext):
        self.ctx = ctx

    def tools(self) -> list[InternalTool]:
        return [
            InternalTool(
                name="GatherUserInfo",
                description="Compiles a short expose about the current chat user from this and past interactions, their personal situation, preferences, etc..",
                params={},
                result="string",
                function=self.tool_gather_user_infos,
            ),
            InternalTool(
                name="SearchChats",
                description="Search this and past interactions about information on the given topic and summarize the findings.",
                params={"search_query": "string"},
                result="string",
                function=self.tool_search_chats,
            ),
        ]

    async def tool_search_chats(self, search_query: str) -> str:
        messages = [[f"{m.role}: {m.content}" for m in chat.messages] for chat in self.ctx.session.chats.values()]
        query = dedent(f"""
            In the following is the full transcript of all past interactions between the User and the LLM Assistant:
            
            {json.dumps(messages, indent=2)}

            Use this transcript to answer the following query:

            {search_query}
        """)
        try:
            res = await self.ctx.query(query)
            return res.content
        except Exception as e:
            return f"Search failed: {e}"

    async def tool_gather_user_infos(self) -> str:
        search_query = "Compile a short exposÃ© about the current chat user, their personal situation, preferences, etc.."
        return await self.tool_search_chats(search_query)
