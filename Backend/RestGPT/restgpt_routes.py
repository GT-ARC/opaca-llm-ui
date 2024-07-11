from typing import Dict, Optional, List, Tuple

import json
import logging

from langchain_community.utilities import Requests
from pydantic import BaseModel

from ..opaca_proxy import proxy as opaca_proxy
from .utils import OpacaLLM, ColorPrint, get_reduced_action_spec
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
    messages: List[Tuple[str, str]] = []

    async def query(self, message: str, debug: bool) -> Dict:
        llm = OpacaLLM(LLM_URL)

        request_wrapper = Requests()

        try:
            action_spec = get_reduced_action_spec(opaca_proxy.get_actions_openapi())
        except Exception as e:
            print(str(e))
            return {"result": "I am sorry, but there occurred an error during the action retrieval. "
                              "Please make sure the opaca platform is running and you are connected.", "debug": str(e)}

        rest_gpt = RestGPT(llm, action_spec=action_spec, requests_wrapper=request_wrapper,
                           simple_parser=False, request_headers={})

        result = rest_gpt.invoke({"query": message, "history": self.messages})
        self.messages.append((message, result["result"]))

        # "result" contains the answer intended for a normal user
        # while "debug" contains all messages from the llm chain
        return {"result": result["result"], "debug": result["debug"] if debug else ""}

    async def history(self) -> list:
        return self.messages

    async def reset(self):
        self.messages = []
