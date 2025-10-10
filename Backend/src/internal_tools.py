"""
Wrapper for different internal tools, to be provided to the OPACA LLM as "actions" like OPACA,
but implemented directly in the backend.
For now, the internal tools are added to the OPACA Proxy's actions, which then delegates back
to this class, so the LLM Methods don't have to be adapted, but mid-term this could be changed.

Some of the tools (like execute-later or maybe summarize-file) may again issue LLM calls. For
this, it would be good if those would have access to the same session. Not sure how best to do this.
"""

import asyncio
import logging
import json

from pydantic import BaseModel
from typing import Callable
from textwrap import dedent

from .models import SessionData, Chat, PendingCallback, PushMessage


MAGIC_NAME = "LLM-Assistant"

logger = logging.getLogger(__name__)


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    result: str
    function: Callable


class InternalTools:

    def __init__(self, session: SessionData, agent_method: 'AbstractMethod'):
        self.session = session
        self.agent_method = agent_method
        self.tools = [
            InternalTool(
                name="ExecuteLater",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The query has to be self-contained, so the LLM can infer the action(s) to be called and their parameters, but it can be natural language, not JSON. The offset should be a time in seconds from now.",
                params={"query": "string", "offset_seconds": "integer"},
                result="boolean",
                function=self.tool_execute_later,
            ),
            InternalTool(
                name="GatherUserInfo",
                description="Compiles a short expose about the current chat user from this and past interactions, their personal situation, preferences, etc..",
                params={},
                result="string",
                function=self.gather_user_infos,
            ),
            InternalTool(
                name="SearchChats",
                description="Search this and past interactions about information on the given topic and summarize the findings.",
                params={"search_query": "string"},
                result="string",
                function=self.search_chats,
            ),
        ]

    def get_internal_tools_simple(self) -> dict[str, dict]:
        """return internal tools in OPACA format used by simple agent"""
        return {
            MAGIC_NAME: [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        key: {"type": val, "required": True}
                        for key, val in tool.params.items()
                    },
                    "result": {"type": tool.result, "required": True}
                }
                for tool in self.tools
            ]
        }

    def get_internal_tools_openai(self) -> list[dict]:
        """return internal tools in OpenAI Functions format"""
        return [
            {
                "type": "function",
                "name": MAGIC_NAME + "--" + tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        key: {"type": val}
                        for key, val in tool.params.items()
                    },
                    "additionalProperties": False,
                    "required": list(tool.params),
                }
            }
            for tool in self.tools
        ]

    async def call_internal_tool(self, tool: str, parameters: dict):
        callback = next(t.function for t in self.tools if t.name == tool)
        return await callback(**parameters)


    # IMPLEMENTATIONS OF ACTUAL TOOLS

    async def tool_execute_later(self, query: str, offset_seconds: int) -> str:
        async def _callback():
            logger.info("WAITING...")
            await asyncio.sleep(offset_seconds)
            logger.info("CALLING LLM NOW...")
            try:
                await self.send_to_websocket(PendingCallback(query=query))

                query_extra = "\n\nNOTE: This query was triggered by the 'execute-later' tool. If it says to 'remind' the user of something, just output that thing the user asked about, e.g. 'You asked me to remind you to ...'; do NOT create another 'execute-later' reminder! If it just asked you to do something by that time, just do it and report on the results as usual."
                res = await self.agent_method.query(query + query_extra, Chat(chat_id=''))
                logger.info(f"EXECUTE LATER RESULT: {res.content}")

                await self.send_to_websocket(PushMessage(**res.model_dump()))

            except Exception as e:
                logger.error(f"EXECUTE LATER FAILED: {e}")
                # TODO send error

        asyncio.create_task(_callback())
        return True

    async def search_chats(self, search_query: str) -> str:
        messages = [[f"{m.role}: {m.content}" for m in chat.messages] for chat in self.session.chats.values()]
        query = dedent(f"""
        In the following is the full transcript of all past interactions between the User and the LLM Assistant:
        
        {json.dumps(messages, indent=2)}

        Use this transcript to answer the following query:

        {search_query}
        """)
        try:
            res = await self.agent_method.query(query, Chat(chat_id=''))
            return res.content
        except Exception as e:
            return f"Search failed: {e}"

    async def gather_user_infos(self) -> str:
        search_query = "Compile a short expose about the current chat user, their personal situation, preferences, etc..",
        return await self.search_chats(search_query)
    
    async def send_to_websocket(self, msg):
        if self.session.websocket:
            await self.session.websocket.send_json(msg.model_dump_json())
