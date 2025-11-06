import decimal
import functools
import logging
import asyncio

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
        self.connected = False
        self.login_lock = asyncio.Lock()
        self.logged_in_containers = set()  # Stores the container ids where the user is currently logged in

    async def connect(self, url: str, user: str, pwd: str):
        """Connect with OPACA platform, get access token if necessary and try to fetch actions.
        Returns the original HTTP Status code returned by the OPACA Platform as the result body.
        """
        self.url = url
        self.connected = False
        try:
            await self._get_token(user, pwd)
            await self.get_actions_simple()
            self.connected = True
            logger.info(f"Connected to {url}")
            return 200
        except httpx.ConnectError as e:
            logger.warning(f"Could not connect: {e}")
            self.url = None
            return 404
        except httpx.HTTPStatusError as e:
            logger.warning(f"Connected with error: {e}")
            self.url = None
            return e.response.status_code if e.response is not None else 400

    async def disconnect(self) -> None:
        """Clears authentication and connection state."""
        for cid in list(self.logged_in_containers):
            await self.deferred_container_logout(cid, 0)
        self.token = None
        self.url = None
        self.connected = False
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

    async def container_login(self, container_id: str, username: str, password: str, timeout: int):
        """Initiate container login for OPACA RP"""
        logger.info(f"Login to container {container_id}")
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.url}/containers/login/{container_id}", json={"username": username, "password": password}, headers=self._headers(), timeout=None)
        res.raise_for_status()

        # Mark container as logged in and schedule logout after timeout seconds
        self.logged_in_containers.add(container_id)
        asyncio.create_task(self.deferred_container_logout(container_id, timeout))

    async def deferred_container_logout(self, container_id: str, delay_seconds: int):
        """Initiate delayed container logout for OPACA RP"""
        try:
            await asyncio.sleep(delay_seconds)
        finally:
            async with self.login_lock:
                # If container was logged out during sleep, do not logout again
                if container_id not in self.logged_in_containers:
                    return

                logger.info(f"Logout of container {container_id}")
                async with httpx.AsyncClient() as client:
                    await client.post(f"{self.url}/containers/logout/{container_id}", headers=self._headers())
                    self.logged_in_containers.remove(container_id)

    async def get_most_likely_container_id(self, agent: str, action: str) -> tuple[str, str]:
        """Get most likely container id and name for given agent and action. Returns empty string if no match found."""
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.url}/containers", headers=self._headers())
        res.raise_for_status()

        # Return the containerId and container name of the first matching container to include the given agent and action
        return next((c["containerId"], c["image"].get("name", c["image"]["imageName"])) for c in res.json()
                    for a in c["agents"] if a["agentId"] == agent and any(action == ac["name"] for ac in a["actions"]))

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
