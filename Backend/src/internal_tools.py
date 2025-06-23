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

MAGIC_NAME = "LLM-Assistant"

class InternalTools:

    def __init__(self, session_id):
        self.session_id = session_id

    def get_internal_tools(self):
        return {
            MAGIC_NAME: [
                {
                    "name": "ExecuteLater",
                    "description": "Schedule some action to be executed later. The query is just another natural-language query that will be sent back to the LLM, having access to the same tools as the 'main' LLM. The offset should be a time in seconds from now.",
                    "parameters": {
                        "query": {"type": "string", "required": True},
                        "offset_seconds": {"type": "integer", "required": True}
                    },
                    "result": {"type": "boolean", "required": True}
                },
            ]
        }
    
    async def call_internal_tool(self, tool: str, parameters: dict):
        tools = {
            "ExecuteLater": self.tool_execute_later
        }
        return await tools[tool](**parameters)

    async def tool_execute_later(self, query, offset_seconds) -> str:
        async def _callback():
            print("waiting...")
            await asyncio.sleep(offset_seconds)
            print("calling LLM now...")
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "http://10.42.5.204:3001/simple/query",
                    json={"user_query": query},
                    cookies={"session_id": self.session_id}
                )
                print("RESULT", res.text)

        asyncio.create_task(_callback())
        return "callback created"
