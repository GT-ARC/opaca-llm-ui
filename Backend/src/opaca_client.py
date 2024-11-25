"""
Client for OPACA Runtime Platform, for establishing a connection, managing access tokens,
getting list of available actions in different formats, and invoking actions.
"""

import decimal
import functools

import jsonref
import requests
from requests.exceptions import ConnectionError, HTTPError
from typing import Optional


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
            self._get_token(user, pwd)
            self._update_opaca_actions()
            return 200
        except (ConnectionError, HTTPError) as e:
            print("COULD NOT CONNECT", e)
            return e.response.status_code if e.response is not None else 400
        
    async def get_actions(self) -> dict[str, list[str]]:
        return {
            agent["agentId"]: [action["name"] for action in agent["actions"]]
            for agent in self.actions_dict
        }
    
    def invoke_opaca_action(self, action: str, agent: Optional[str], params: dict) -> dict:
        agent = f"/{agent}" if agent else ""
        res = requests.post(f"{self.url}/invoke/{action}{agent}", json=params, headers=self._headers())
        res.raise_for_status()
        return res.json()

    def get_actions_openapi(self):
        try:
            # Will return actions as JSON
            res = requests.get(f'{self.url}/v3/api-docs/actions', headers=self._headers())
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print("COULD NOT GET ACTIONS", e)
            return {}

    def get_actions_with_refs(self):
        try:
            # Returns the action lists with already replaced references for openai function usage
            loader = functools.partial(jsonref.jsonloader, parse_float=decimal.Decimal)
            return jsonref.load_uri(f'{self.url}/v3/api-docs/actions', loader=loader)
        except Exception as e:
            print("COULD NOT GET ACTIONS", e)
            return {}

    def _update_opaca_actions(self):
        try:
            res = requests.get(f"{self.url}/agents", headers=self._headers())
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

    def _get_token(self, user, pwd):
        self.token = None
        if user and pwd:
            res = requests.post(f"{self.url}/login", json={"username": user, "password": pwd})
            res.raise_for_status()
            self.token = res.text


# pseudo "singleton" instance of the client to be used by the other modules by importing from this module
client = OpacaClient()
