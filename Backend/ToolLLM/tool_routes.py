from typing import Dict, Optional, List

import logging
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..RestGPT import ColorPrint, get_reduced_action_spec, build_prompt
from ..opaca_proxy import proxy as opaca_proxy
from .utils import transform_to_openai_tools

logger = logging.getLogger()

logging.basicConfig(
    format="%(message)s",
    handlers=[logging.StreamHandler(ColorPrint())],
    level=logging.INFO
)


class ToolLLMBackend:
    messages: List = []
    llm_type: str
    llm: BaseChatModel | ChatOpenAI

    def __init__(self, llm_type: str):
        self.llm_type = llm_type
        # This is the DEFAULT config
        self.config = {
            "temperature": 0,
        }

    async def query(self, message: str, debug: bool, api_key: str) -> Dict:

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(api_key)
        except ValueError as e:
            return {"result": "You are trying to use a model which uses an api key but provided none. Please "
                              "enter a valid api key and try again.", "debug": str(e)}

        # TODO get "tools" from opaca-proxy and bind to llm
        tools = transform_to_openai_tools(get_reduced_action_spec(opaca_proxy.get_actions_openapi()))

        # INITIAL QUERY
        prompt = build_prompt(
            system_prompt="You are a helpful ai assistant that plans solution to user queries with the help of tools. "
                          "You can find those tools in the tool section. "
                          "Some queries require sequential calls with those tools."
                          "If you are unable to fulfill the user queries with the given tools, let the user know."
                          "You are only allowed to use those given tools. If a user asks about tools directly, answer "
                          "them with the required information. Tools can also be described as services. You ",
            examples=[],
            input_variables=['input'],
            message_template="{input}"
        )
        chain = prompt | self.llm.bind_tools(tools=tools)
        result = chain.invoke({'input': message})

        # Execute generated tools
        tool_names = []
        tool_params = []
        tool_results = []
        for call in result.tool_calls:
            tool_names.append(call['name'])
            tool_params.append(call['args'])
            tool_results.append(opaca_proxy.invoke_opaca_action(call['name'], None, call['args']))

        if len(tool_names) > 0:
            prompt_template = PromptTemplate(
                template="You just used the tools {tool_names} with the following parameters: {parameters}."
                         "The results were {results}."
                         "Generate a response explaining the result to a user.",
                input_variables=['tool_names', 'parameters', 'results'],
            )
            response_chain = prompt_template | self.llm.bind_tools(tools=tools)
            result = response_chain.invoke({
                'tool_names': tool_names,
                'parameters': tool_params,
                'results': tool_results
            })

        """
        try:
            result = rest_gpt.invoke({"query": message, "history": self.messages, "config": self.config})
        except openai.AuthenticationError as e:
            return {"result": "I am sorry, but your provided api key seems to be invalid. Please provide a valid "
                              "api key and try again.", "debug": str(e)}
        self.messages.append(HumanMessage(message))
        self.messages.append(AIMessage(result["result"]))
        """
        # "result" contains the answer intended for a normal user
        # while "debug" contains all messages from the llm chain
        return {"result": result.content, "debug": "" if debug else ""}

    async def history(self) -> list:
        return self.messages

    async def reset(self):
        self.messages = []

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = conf

    def init_model(self, api_key: str):
        api_key = api_key or os.getenv("OPENAI_API_KEY")  # if empty, use from Env
        if self.llm_type == "gpt-4o":
            self.check_for_key(api_key)
            self.llm = ChatOpenAI(model="gpt-4o", temperature=self.config["temperature"], openai_api_key=api_key)
        elif self.llm_type == "gpt-4o-mini":
            self.check_for_key(api_key)
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=self.config["temperature"], openai_api_key=api_key)

    @staticmethod
    def check_for_key(api_key: str):
        if not api_key:
            raise ValueError("No api key provided")
