import decimal
import functools
import logging
import asyncio
import requests
import httpx
import jsonref
from typing import Optional, List, Any
from opaca import AsyncOpacaClient
from opaca.models import ActionDescription, ContainerDescription

logger = logging.getLogger(__name__)


# list of string fragments that must NOT appear in the action names, else they will be forbidden
actions_blacklist: List[str] = []


class OpacaClient(AsyncOpacaClient):
    """
    Client for OPACA Runtime Platform, for establishing a connection, managing access tokens,
    getting list of available actions in different formats, and invoking actions.
    """

    def __init__(self, url: str = ''):
        super(OpacaClient, self).__init__(url=url)
        self.connected = False
        self.login_lock = asyncio.Lock()

    async def connect(self, url: str, user: str | None, pwd: str | None):
        """Connect with OPACA platform, get access token if necessary and try to fetch actions.
        Returns the original HTTP Status code returned by the OPACA Platform as the result body.
        """
        self.url = url
        self.connected = False
        self.token = None
        try:
            if user and pwd:
                await self.platform_login(username=user, password=pwd)
            await self.get_info()
            self.connected = True
            logger.info(f"Connected to {url}")
            return 200
        except httpx.ConnectError as e:
            logger.warning(f"Could not connect: {e}")
            self.url = ''
            return 404
        except httpx.HTTPStatusError as e:
            logger.warning(f"Connected with error: {e}")
            self.url = ''
            return e.response.status_code if e.response else 400

    async def disconnect(self) -> None:
        """Clears authentication and connection state."""
        await self.logout_all_containers()
        logger.info(f"Disconnected from {self.url}")
        self.token = None
        self.connected = False
        self.url = ''

    async def get_extra_ports(self) -> list[dict[str, Any]]:
        if not self.url: return []
        try:
            containers = await self.get_containers()
            # build dict of all accessible extra codes
            tmp = {}
            for container in containers:
                cid = container.containerId
                token = self.container_tokens.get(cid)
                for k, v in container.connectivity["extraPortMappings"].items():
                    if v["protocol"] == "TCP":
                        url = f'{container.connectivity["publicUrl"]}:{k}'
                        if token: url += f"?token={token}"
                        try:
                            requests.get(url).raise_for_status()
                            if cid not in tmp:
                                tmp[cid] = {
                                    "container": container.image.imageName,
                                    "extraPorts": []
                                }
                            tmp[cid]["extraPorts"].append(
                                {"fullUrl": url, "description": v["description"]}
                            )
                        except Exception as e:
                            logger.warning(f"Could not load extension {url}: {e}")
            return list(tmp.values())

        except Exception as e:
            logger.error(f"Could not get Extra-Ports: {e}")
            raise e

    async def get_actions_simple(self) -> dict[str, List[ActionDescription]]:
        """Get actions of OPACA agents, grouped by agent, but a bit simplified: just agent-ids and actions"""
        return {
            agent.agentId: agent.actions
            for container in await self.get_containers()
            for agent in container.agents
        }
    
    async def get_containers(self) -> list[ContainerDescription]:
        if not self.url: return []
        return await super().get_containers(include_connected=True)

    async def get_actions_openapi(self, inline_refs=False) -> dict:
        """Get actions of OPACA agents in OpenAPI format; if inline_refs is true, datatypes will be
        inlined directly into the action JSON instead of being a separate block.
        """
        if not self.url: return {}
        try:
            res = await self._request('GET', '/v3/api-docs/actions')
            if inline_refs:
                loader = functools.partial(jsonref.jsonloader, parse_float=decimal.Decimal)
                return jsonref.load(res, loader=loader)
            else:
                return res.json()
        except Exception as e:
            logger.error(f"Failed to get OpenAPI actions: {e}")
            raise e

    async def safe_invoke(self, action: str, agent: str | None, params: dict) -> Any | None:
        """
        Invoke the given OPACA agent at the given agent (or any agent) with
        the given parameters. Considers blacklisted agents and actions.
        """
        blacklist = [a.lower() for a in actions_blacklist]
        if any(x in action.lower() for x in blacklist):
            raise Exception(f"Disallowed action: {action}")
        if agent is not None and any(x in agent.lower() for x in blacklist):
            raise Exception(f"Disallowed agent: {agent}")

        try:
            return await self.invoke(action, agent, args=params)
        except Exception as e:
            logger.error(f"Failed to invoke action {action!r}: {e}")
            raise e

    async def container_login(self, container_id: str, username: str, password: str):
        await super().container_login(container_id, username, password)
        logger.info(f"Logged into container {container_id}")

    async def logout_all_containers(self):
        for cid in list(self.container_tokens.keys()):
            await self.deferred_container_logout(cid, 0)

    async def deferred_container_logout(self, container_id: str, delay_seconds: int):
        """Initiate delayed container logout for OPACA RP"""
        try:
            await asyncio.sleep(delay_seconds)
        finally:
            # finally -> make sure that logout still happens even if backend is shut down
            # login-lock -> make sure that container is not logged out while 2nd invoke-attempt is in locked-state
            async with self.login_lock:
                logger.info(f"Logged out of container {container_id}")
                await self.container_logout(container_id)


    async def get_most_likely_container_id(self, agent: str, action: str) -> tuple[str, str]:
        """Get most likely container id and name for given agent and action. Returns empty string if no match found."""
        containers = await self.get_containers()

        # Return the containerId and container name of the first matching container to include the given agent and action
        return next(
            (c.containerId, c.image.name or c.image.imageName)
            for c in containers
            for a in c.agents
            if a.agentId == agent and any(action == ac.name for ac in a.actions)
        )
