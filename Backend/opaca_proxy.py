import requests
from typing import Optional

# TODO use aiohttp?


class OpacaProxy:

    def __init__(self):
        self.url = None
        self.token = None
        self.actions = "(No services, not connected yet.)"
        
    async def connect(self, url: str, user: str, pwd: str):
        print("CONNECT", repr(url), user, pwd)
        self.url = url

        try:
            self._get_token(user, pwd)
            requests.get(f"{self.url}/info", headers=self._headers()).raise_for_status()
            self._update_opaca_actions()
            return True
        except Exception as e:
            print("COULD NOT CONNECT", e)
            return False
    
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

    def _update_opaca_actions(self):
        try:
            res = requests.get(f"{self.url}/agents", headers=self._headers())
            res.raise_for_status()
            self.actions = res.text
        except Exception as e:
            print("COULD NOT CONNECT", e)
            self.actions = "(No Services. Failed to connect to OPACA Runtime.)"

    def _headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else None

    def _get_token(self, user, pwd):
        self.token = None
        if user and pwd:
            res = requests.post(f"{self.url}/login", json={"username": user, "password": pwd})
            res.raise_for_status()
            self.token = res.text


# pseudo "singleton" instance of the proxy to be used by the other modules by importing from this module
proxy = OpacaProxy()
