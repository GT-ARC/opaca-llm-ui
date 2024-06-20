from typing import Dict, Optional

import json
import logging

from langchain_community.utilities import Requests
from pydantic import BaseModel

from ..opaca_proxy import proxy as opaca_proxy
from .utils import OpacaLLM, ColorPrint
from .rest_gpt import RestGPT

LLM_URL = "http://10.0.64.101"

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


class RestGptBackend:

    async def query(self, message: str) -> str:
        llm = OpacaLLM(LLM_URL)

        request_wrapper = Requests()
        services = opaca_proxy.actions
        action_spec = []
        for agent in json.loads(services):
            for action in agent['actions']:
                action_spec.append(Action(name=action['name'], description=action['description'],
                                        parameters=action['parameters'], result=action['result']))

        rest_gpt = RestGPT(llm, action_spec=action_spec, requests_wrapper=request_wrapper,
                        simple_parser=False, request_headers={})

        return rest_gpt.invoke({"query": message})["result"]

    async def history(self) -> list:
        # TODO not yet implemented
        return []

    async def reset(self):
        # TODO not yet implemented
        pass
