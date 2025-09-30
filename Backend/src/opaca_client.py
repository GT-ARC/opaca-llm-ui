import decimal
import functools
import logging

import httpx
import jsonref
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class OpacaClient:
    """
    Client for OPACA Runtime Platform, for establishing a connection, managing access tokens,
    getting list of available actions in different formats, and invoking actions.
    """

    def __init__(self):
        self.url = None
        self.token = None

    async def connect(self, url: str, user: str, pwd: str):
        """Connect with OPACA platform, get access token if necessary and try to fetch actions.
        Returns the original HTTP Status code returned by the OPACA Platform as the result body.
        """
        self.url = url
        try:
            await self._get_token(user, pwd)
            await self.get_actions_simple()
            logger.info(f"Connected to {url}")
            return 200
        except httpx.ConnectError as e:
            logger.warning(f"Could not connect: {e}")
            return 404
        except httpx.HTTPStatusError as e:
            logger.warning(f"Connected with error: {e}")
            return e.response.status_code if e.response is not None else 400

    async def disconnect(self) -> None:
        """Clears authentication and connection state."""
        self.token = None
        self.url = None
        logger.info(f"Disconnected")

    async def get_actions(self) -> dict:
        """Get actions of OPACA agents, in original OPACA format."""
        try:
            if not self.url:
                return {}
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/agents", headers=self._headers())
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.error(f"Could not get Actions: {e}")
            raise e

    async def get_actions_simple(self) -> dict[str, List[Dict[str, Any]]]:
        """Get actions of OPACA agents, grouped by agent, but a bit simplified: just agent-ids and actions"""
        return {
            agent["agentId"]: agent["actions"] for agent in await self.get_actions()
        }

    async def get_actions_openapi(self, inline_refs=False):
        """Get actions of OPACA agents in OpenAPI format; if inline_refs is true, datatypes will be
        inlined directly into the action JSON instead of being a separate block.
        """
        try:
            if not self.url:
                return {}
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.url}/v3/api-docs/actions", headers=self._headers())
            res.raise_for_status()
            if inline_refs:
                loader = functools.partial(jsonref.jsonloader, parse_float=decimal.Decimal)
                return jsonref.load(res, loader=loader)
            else:
                return res.json()
        except Exception as e:
            logger.error(f"Could not get Actions: {e}")
            raise e

    async def invoke_opaca_action(self, action: str, agent: Optional[str], params: dict) -> dict:
        """Invoke the given OPACA agent at the given agent (or any agent) with given parameters."""
        agent = f"/{agent}" if agent else ""
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.url}/invoke/{action}{agent}", json=params, headers=self._headers(), timeout=None)
        res.raise_for_status()
        return res.json()

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else None

    async def _get_token(self, user, pwd):
        """Get and store JWT access token for OPACA RP"""
        self.token = None
        if user and pwd:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self.url}/login", json={"username": user, "password": pwd})
            res.raise_for_status()
            self.token = res.text
