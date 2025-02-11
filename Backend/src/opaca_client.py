"""
Client for OPACA Runtime Platform, for establishing a connection, managing access tokens,
getting list of available actions in different formats, and invoking actions.
"""

import decimal
import functools

import httpx
import jsonref
from requests.exceptions import ConnectionError, HTTPError
from typing import Optional, List, Dict, Any


class OpacaClient:

    def __init__(self):
        self.url = None
        self.token = None
        self.actions = "(No services, not connected yet.)"
        self.actions_dict = {}
        
    async def connect(self, url: str, user: str, pwd: str):
        print("CONNECT", repr(url), user)
        self.url = url

        try:
            await self._get_token(user, pwd)
            await self._update_opaca_actions()
            return 200
        except (ConnectionError, HTTPError) as e:
            print("COULD NOT CONNECT", e)
            return e.response.status_code if e.response is not None else 400
        
    async def get_actions(self) -> dict[str, List[Dict[str, Any]]]:
        return {
            agent["agentId"]: [
                {"name": action["name"], "description": action["description"],
                 "parameters": action["parameters"], "result": action["result"]} for action in agent["actions"]
            ] for agent in self.actions_dict
        }
    
    async def invoke_opaca_action(self, action: str, agent: Optional[str], params: dict) -> dict:
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
