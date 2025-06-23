"""
Client for OPACA Runtime Platform, for establishing a connection, managing access tokens,
getting list of available actions in different formats, and invoking actions.
"""

import decimal
import functools

import httpx
import jsonref
from typing import Optional, List, Dict, Any
from .internal_tools import InternalTools, MAGIC_NAME

class OpacaClient:

    def __init__(self, internal_tools: InternalTools):
        self.url = None
        self.token = None
        self.actions = "(No services, not connected yet.)"
        self.actions_dict = {}
        self.internal_tools = internal_tools
        
    async def connect(self, url: str, user: str, pwd: str):
        print("CONNECT", repr(url), user)
        self.url = url

        try:
            await self._get_token(user, pwd)
            await self._update_opaca_actions()
            return 200
        except httpx.ConnectError as e:
            print("COULD NOT CONNECT", e)
            return 404
        except httpx.HTTPStatusError as e:
            print("CONNECTED WITH ERROR", e)
            return e.response.status_code if e.response is not None else 400
        
    async def get_actions(self) -> dict[str, List[Dict[str, Any]]]:
        return dict(**{
            agent["agentId"]: agent["actions"] for agent in self.actions_dict
        }, **self.internal_tools.get_internal_tools())

    async def get_agent_details(self) -> Dict[str, Dict[str, Any]]:
        try:
            await self._update_opaca_actions()
        except:
            # exception is handled within the above method
            pass
        return {
            agent["agentId"]: {
                "description": agent["description"],
                "functions": [action["name"] for action in agent["actions"]]
            }
            for agent in self.actions_dict
        }
    
    async def invoke_opaca_action(self, action: str, agent: Optional[str], params: dict) -> dict:
        if agent == MAGIC_NAME:
            return await self.internal_tools.call_internal_tool(action, params)

        agent = f"/{agent}" if agent else ""
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.url}/invoke/{action}{agent}", json=params, headers=self._headers(), timeout=None)
        res.raise_for_status()
        return res.json()

    async def get_actions_openapi(self):
        try:
            # Will return actions as JSON
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/v3/api-docs/actions", headers=self._headers())
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print("COULD NOT GET ACTIONS", e)
            return {}

    async def get_actions_with_refs(self):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/v3/api-docs/actions", headers=self._headers())
                # Returns the action lists with already replaced references for openai function usage
                loader = functools.partial(jsonref.jsonloader, parse_float=decimal.Decimal)
                return jsonref.load(res, loader=loader)
        except Exception as e:
            print("COULD NOT GET ACTIONS", e)
            return {}

    async def _update_opaca_actions(self):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/agents", headers=self._headers())
            res.raise_for_status()
            self.actions = res.text
            self.actions_dict = res.json()
        except Exception as e:
            print("COULD NOT UPDATE ACTIONS", e)
            self.actions = "(No Services. Failed to connect to OPACA Runtime.)"
            self.actions_dict = {}
            raise e

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else None

    async def _get_token(self, user, pwd):
        self.token = None
        if user and pwd:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self.url}/login", json={"username": user, "password": pwd})
            res.raise_for_status()
            self.token = res.text
