"""
Wrapper for different internal tools, to be provided to the OPACA LLM as "actions" like OPACA,
but implemented directly in the backend.
For now, the internal tools are added to the OPACA Proxy's actions, which then delegates back
to this class, so the LLM Methods don't have to be adapted, but mid-term this could be changed.

Some of the tools (like execute-later or maybe summarize-file) may again issue LLM calls. For
this, it would be good if those would have access to the same session. Not sure how best to do this.
"""

import asyncio
import httpx
import logging

from pydantic import BaseModel
from typing import Callable


MAGIC_NAME = "LLM-Assistant"

logger = logging.getLogger(__name__)


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    result: str
    function: Callable


class InternalTools:

    def __init__(self, session_id):
        self.session_id = session_id
        self.tools = [
            InternalTool(
                name="ExecuteLater",
                description="Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The offset should be a time in seconds from now.",
                params={"query": "string", "offset_seconds": "integer"},
                result="boolean",
                function=self.tool_execute_later,
            )
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

    async def tool_execute_later(self, query, offset_seconds) -> str:
        async def _callback():
            logger.info("WAITING...")
            await asyncio.sleep(offset_seconds)
            logger.info("CALLING LLM NOW...")
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "http://10.42.4.246:3001/query/simple",
                    json={"user_query": query},
                    cookies={"session_id": self.session_id}
                )
                logger.info("RESULT", res.text)

        asyncio.create_task(_callback())
        return "callback created"
