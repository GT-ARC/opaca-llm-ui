from typing import Dict, Optional

import requests
import json
import logging

from langchain_community.utilities import Requests
from pydantic import BaseModel

from .utils import OpacaLLM, ColorPrint
from .rest_gpt import RestGPT

OPACA_URL = "http://localhost:8000"
LLM_URL = "http://10.0.64.101"
TOKEN = None

logger = logging.getLogger()

logging.basicConfig(
    format="%(message)s",
    handlers=[logging.StreamHandler(ColorPrint())],
    level=logging.INFO
)


class Action(BaseModel):
    name: str
    description: Optional[str]
    parameters: Dict
    result: Optional[Dict]

    def __str__(self):
        return f'{self.name}, Description: {self.description}, Parameters: {self.parameters}, Result: {self.result}'


def headers():
    return {'Authorization': f'Bearer {TOKEN}'} if TOKEN else None


def get_token(user, pwd):
    global TOKEN
    TOKEN = None
    if user and pwd:
        res = requests.post(f"{OPACA_URL}/login", json={"username": user, "password": pwd})
        res.raise_for_status()
        TOKEN = res.text


def get_opaca_services():
    try:
        res = requests.get(f"{OPACA_URL}/agents", headers=headers())
        res.raise_for_status()
        return res.text
    except Exception as e:
        print("COULD NOT CONNECT", e)
        return "(No Services. Failed to connect to OPACA Runtime.)"


async def connect(url: str, user: str, pwd: str):
    print("CONNECT", repr(url), user, pwd)
    global OPACA_URL
    OPACA_URL = url

    try:
        get_token(user, pwd)
        requests.get(f"{OPACA_URL}/info", headers=headers()).raise_for_status()
        return True
    except Exception as e:
        print("COULD NOT CONNECT", e)
        return False


async def query(message: str) -> str:
    llm = OpacaLLM(LLM_URL)

    request_wrapper = Requests()
    services = get_opaca_services()

    action_spec = []
    for agent in json.loads(services):
        for action in agent['actions']:
            action_spec.append(Action(name=action['name'], description=action['description'],
                                      parameters=action['parameters'], result=action['result']))

    rest_gpt = RestGPT(llm, action_spec=action_spec, requests_wrapper=request_wrapper,
                       simple_parser=False, request_headers=headers())

    return rest_gpt.invoke({"query": message})["result"]


async def history():
    return "TODO not yet implemented"


async def reset():
    return "TODO not yet implemented"
