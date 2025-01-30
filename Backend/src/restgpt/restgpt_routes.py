import time
from typing import Dict, Optional

import os

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..llama_proxy import LlamaProxy
from ..models import Response, SessionData, OpacaLLMBackend, ConfigParameter
from ..utils import get_reduced_action_spec
from .rest_gpt import RestGPT


class Action(BaseModel):
    name: str
    description: Optional[str]
    parameters: Dict
    result: Optional[Dict]

    def __str__(self):
        return f'{self.name}, Description: {self.description}, Parameters: {self.parameters}, Result: {self.result}'


class RestGptBackend(OpacaLLMBackend):
    NAME_OPENAI = "rest-gpt-openai"
    NAME_LLAMA = "rest-gpt-llama"
    use_llama: bool
    llm: BaseChatModel | ChatOpenAI

    def __init__(self, use_llama: bool):
        self.use_llama = use_llama

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session, None)

    async def query_stream(self, message: str, session: SessionData, websocket=None) -> Response:

        # Set config
        config = session.config.get(
            RestGptBackend.NAME_LLAMA if self.use_llama else RestGptBackend.NAME_OPENAI,
            self.default_config()
        )

        # Create response object
        response = Response()
        response.query = message

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(session.api_key, config)
        except ValueError as e:
            response.content = ("You are trying to use a model which uses an api key but provided none. Please "
                                "enter a valid api key and try again.")
            response.error = str(e)
            return response

        try:
            action_spec = get_reduced_action_spec(await session.client.get_actions_with_refs())
        except Exception as e:
            response.content = ("I am sorry, but there occurred an error during the action retrieval. "
                                "Please make sure the opaca platform is running and connected.")
            response.error = str(e)
            return response

        rest_gpt = RestGPT(self.llm, action_spec)

        try:
            total_time = time.time()
            result = await rest_gpt.ainvoke({
                "query": message,
                "history": session.messages,
                "config": config,
                "response": response,
                "client": session.client,
                "websocket": websocket,
            })
            response.execution_time = time.time() - total_time
        except openai.AuthenticationError as e:
            response.content = ("I am sorry, but your provided api key seems to be invalid. Please provide a valid "
                                "api key and try again.")
            response.error = str(e)
            return response
        session.messages.append(HumanMessage(message))
        session.messages.append(AIMessage(result.content))

        return response

    @property
    def config_schema(self) -> Dict[str, ConfigParameter]:
        """
        Declares the default configuration
        """
        config = {
            "slim_prompts": ConfigParameter(        # Use slim prompts -> cheaper
                type="object",
                required=True,
                default={
                    "planner": ConfigParameter(type="boolean", required=True, default=True),
                    "action_selector": ConfigParameter(type="boolean", required=True, default=True),
                    "evaluator": ConfigParameter(type="boolean", required=True, default=False)
                }),
            "examples": ConfigParameter(            # How many examples are used per agent
                type="object",
                required=True,
                default={
                    "planner": ConfigParameter(type="boolean", required=True, default=False),
                    "action_selector": ConfigParameter(type="boolean", required=True, default=True),
                    "caller": ConfigParameter(type="boolean", required=True, default=True),
                    "evaluator": ConfigParameter(type="boolean", required=True, default=True)
                }),
            "use_agent_names": ConfigParameter(type="boolean", required=True, default=True),
        }

        if self.use_llama:
            config.update({
                "llama-url": ConfigParameter(type="string", required=True, default="http://10.0.64.101:11000"),
                "llama-model": ConfigParameter(type="string", required=True, default="llama3.1:70b"),
            })
        else:
            config.update({
                "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),  # Temperature for models
                "gpt-model": ConfigParameter(type="string", required=True, default="gpt-4o-mini"),
            })

        return config

    def init_model(self, api_key: str, config: dict):
        api_key = api_key or os.getenv("OPENAI_API_KEY")  # if empty, use from Env
        if self.use_llama:
            self.llm = LlamaProxy(
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
