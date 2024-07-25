from typing import Dict, Optional, List

import logging

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..opaca_proxy import proxy as opaca_proxy
from .utils import OpacaLLM, ColorPrint, get_reduced_action_spec
from .rest_gpt import RestGPT

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
    messages: List = []
    llm_type: str
    llm: BaseChatModel | ChatOpenAI

    def __init__(self, llm_type: str):
        self.llm_type = llm_type

    async def query(self, message: str, debug: bool, api_key: str) -> Dict:

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(api_key)
        except ValueError as e:
            return {"result": "You are trying to use a model which uses an api key but provided none. Please "
                              "enter a valid api key and try again.", "debug": str(e)}

        try:
            action_spec = get_reduced_action_spec(opaca_proxy.get_actions_openapi())
        except Exception as e:
            print(str(e))
            return {"result": "I am sorry, but there occurred an error during the action retrieval. "
                              "Please make sure the opaca platform is running and connected.", "debug": str(e)}

        rest_gpt = RestGPT(self.llm, action_spec=action_spec)

        try:
            result = rest_gpt.invoke({"query": message, "history": self.messages})
        except openai.AuthenticationError as e:
            return {"result": "I am sorry, but your provided api key seems to be invalid. Please provide a valid "
                              "api key and try again.", "debug": str(e)}
        self.messages.append(HumanMessage(message))
        self.messages.append(AIMessage(result["result"]))

        # "result" contains the answer intended for a normal user
        # while "debug" contains all messages from the llm chain
        return {"result": result["result"], "debug": result["debug"] if debug else ""}

    async def history(self) -> list:
        return self.messages

    async def reset(self):
        self.messages = []

    def init_model(self, api_key: str):
        if self.llm_type == "llama3":
            self.llm = OpacaLLM()
        elif self.llm_type == "gpt-4o":
            self.check_for_key(api_key)
            self.llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=api_key)
        elif self.llm_type == "gpt-3.5-turbo":
            self.check_for_key(api_key)
            self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=api_key)

    @staticmethod
    def check_for_key(api_key: str):
        if not api_key:
            raise ValueError("No api key provided")
