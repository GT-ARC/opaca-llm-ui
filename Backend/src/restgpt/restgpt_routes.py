import time
from typing import Dict, Optional

import logging
import os

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..models import Response, SessionData
from .utils import OpacaLLM
from ..utils import get_reduced_action_spec, ColorPrint
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
    use_llama: bool
    llm: BaseChatModel | ChatOpenAI

    def __init__(self, use_llama: bool):
        self.use_llama = use_llama

    async def query(self, message: str, debug: bool, api_key: str, session: SessionData) -> Response:

        # Set config
        config = session.config.get(f'rest-gpt-{"llama" if self.use_llama else "openai"}', await self.get_config())

        # Create response object
        response = Response()
        response.query = message

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(api_key, config)
        except ValueError as e:
            response.content = ("You are trying to use a model which uses an api key but provided none. Please "
                                "enter a valid api key and try again.")
            response.error = str(e)
            return response

        try:
            action_spec = get_reduced_action_spec(session.client.get_actions_with_refs())
        except Exception as e:
            response.content = ("I am sorry, but there occurred an error during the action retrieval. "
                                "Please make sure the opaca platform is running and connected.")
            response.error = str(e)
            return response

        rest_gpt = RestGPT(self.llm, action_spec=action_spec)

        try:
            total_time = time.time()
            result = rest_gpt.invoke({
                "query": message,
                "history": session.messages,
                "config": config,
                "response": response,
                "client": session.client,
            })["result"]
            response.execution_time = time.time() - total_time
        except openai.AuthenticationError as e:
            response.content = ("I am sorry, but your provided api key seems to be invalid. Please provide a valid "
                                "api key and try again.")
            response.error = str(e)
            return response
        session.messages.append(HumanMessage(message))
        session.messages.append(AIMessage(result.content))

        return response

    async def get_config(self) -> dict:
        """
        Declares the default configuration
        """
        config = {
            "slim_prompts": {                       # Use slim prompts -> cheaper
                "planner": True,
                "action_selector": True,
                "evaluator": False
            },
            "examples": {                           # How many examples are used per agent
                "planner": False,
                "action_selector": True,
                "caller": True,
                "evaluator": True
            },
            "use_agent_names": True,
        }

        if self.use_llama:
            config.update({
                "llama-url": "http://10.0.64.101:11000",
                "llama-model": "llama3.1:70b",
            })
        else:
            config.update({
                "temperature": 0,  # Temperature for models
                "gpt-model": "gpt-4o-mini",
            })

        return config

    def init_model(self, api_key: str, config: dict):
        api_key = api_key or os.getenv("OPENAI_API_KEY")  # if empty, use from Env
        if self.use_llama:
            self.llm = OpacaLLM(
                url=config['llama-url'],
                model=config['llama-model']
            )
        else:
            self.check_for_key(api_key)
            self.llm = ChatOpenAI(
                model=config["gpt-model"],
                temperature=float(config["temperature"]),
                openai_api_key=api_key
            )

    @staticmethod
    def check_for_key(api_key: str):
        if not api_key:
            raise ValueError("No api key provided")
