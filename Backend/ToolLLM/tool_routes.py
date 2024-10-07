import re
from typing import Dict, List

import logging
import os

from colorama import Fore
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..RestGPT import build_prompt
from ..opaca_proxy import proxy as opaca_proxy
from .utils import openapi_to_functions


class ColorPrint:
    def __init__(self):
        self.color_mapping = {
            "Tools": Fore.RED,
            "AI Answer": Fore.GREEN,
            "Query": Fore.WHITE,
        }

    def write(self, data):
        module = data.split(':')[0]
        if module not in self.color_mapping:
            print(data, end="")
        else:
            print(self.color_mapping[module] + data + Fore.RESET, end="")


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
    debug_output: str = ""
    should_continue: bool = True
    max_iter: int = 5

    def __init__(self, llm_type: str):
        self.llm_type = llm_type
        # This is the DEFAULT config
        self.config = {
            "temperature": 0,
            "use_agent_names": True,
        }

    async def query(self, message: str, debug: bool, api_key: str) -> Dict:

        # Initialize parameters
        self.debug_output = f'Query: {message}\n'
        tool_names = []
        tool_params = []
        tool_results = []
        tool_responses = []
        result = None
        c_it = 0
        self.should_continue = True

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(api_key)
        except ValueError as e:
            return {"result": "You are trying to use a model which uses an api key but provided none. Please "
                              "enter a valid api key and try again.", "debug": str(e)}

        try:
            # Convert openapi schema to openai function schema
            tools, error = openapi_to_functions(opaca_proxy.get_actions_with_refs(), self.config['use_agent_names'])
            if len(tools) > 128:
                self.debug_output += (f"WARNING: Your number of tools ({len(tools)}) exceed the maximum tool limit of "
                                      f"128. All tools after index 128 will be ignored!")
            if error:
                self.debug_output += error
        except Exception as e:
            return {"result": "It appears no actions were returned by the Opaca Platform. Make sure you are "
                              "connected to the Opaca Runtime Platform and the platform contains at least one "
                              "action.", "debug": str(e)}

        # Run until request is finished or maximum number of iterations is reached
        while self.should_continue and c_it < self.max_iter:

            # Build first llm agent
            prompt = build_prompt(
                system_prompt="You are a helpful ai assistant that plans solution to user queries with the help of "
                              "tools. You can find those tools in the tool section. Do not generate optional "
                              "parameters for those tools if the user has not explicitly told you to."
                              "Some queries require sequential calls with those tools. If other tool calls have been "
                              "made already, you will receive the generated AI response of these tool calls. In that "
                              "case you should continue to fulfill the user query with the additional knowledge. "
                              "If you are unable to fulfill the user queries with the given tools, let the user know. "
                              "You are only allowed to use those given tools. If a user asks about tools directly, "
                              "answer them with the required information. Tools can also be described as services.",
                examples=[],
                input_variables=['input'],
                message_template="Human: {input}{scratchpad}"
            )
            chain = prompt | self.llm.bind_tools(tools=tools[:128])
            result = chain.invoke({
                'input': message,
                'scratchpad': self.build_scratchpad(tool_responses),    # scratchpad contains ai responses
                'history': self.messages
            })

            # Check if tools were generated and if so, execute them by calling the opaca-proxy
            for call in result.tool_calls:
                tool_names.append(call['name'])
                tool_params.append(call['args'])
                try:
                    if self.config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    tool_results.append(
                        opaca_proxy.invoke_opaca_action(
                            action_name,
                            agent_name,
                            call['args']['requestBody'] if 'requestBody' in call['args'] else {}
                        ))
                except Exception as e:
                    tool_results.append(str(e))
                self.debug_output += (f'Tool {len(tool_names)}: '
                                      f'{call["name"]}, '
                                      f'{call["args"]["requestBody"] if "requestBody" in call["args"] else {}}, '
                                      f'{tool_results[-1]}\n')

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tool_calls) > 0:
                # Build second llm agent
                prompt_template = PromptTemplate(
                    template="A user had the following request: {query}\n"
                             "You just used the tools {tool_names} with the following parameters: {parameters}\n"
                             "The results were {results}\n"
                             "Generate a response explaining the result to a user. Decide if the user request "
                             "requires further tools by outputting 'CONTINUE' or 'FINISHED' at the end of your "
                             "response.",
                    input_variables=['query', 'tool_names', 'parameters', 'results'],
                )
                response_chain = prompt_template | self.llm.bind_tools(tools=tools[:128])
                result = response_chain.invoke({
                    'query': message,               # Original user query
                    'tool_names': tool_names,       # ALL the tools used so far
                    'parameters': tool_params,      # ALL the parameters used for the tools
                    'results': tool_results         # ALL the results from the opaca action calls
                })

                # Check if llm agent thinks user query has not been fulfilled yet
                self.should_continue = True if re.search(r"\bCONTINUE\b", result.content) else False

                # Remove the keywords from the generated response
                result.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result.content).strip()

                # Add generated response to internal history to give result to first llm agent
                tool_responses.append(AIMessage(result.content))
            else:
                self.should_continue = False

            self.debug_output += f'AI Answer: {result.content}\n'
            c_it += 1

        # Add query and final response to global message history
        self.messages.append(HumanMessage(message))
        self.messages.append(AIMessage(result.content))

        # "result" contains the answer intended for a normal user
        # "debug" contains all internal messages
        return {"result": result.content, "debug": self.debug_output if debug else ""}

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

    @staticmethod
    def build_scratchpad(messages: List[AIMessage]) -> str:
        out = ''
        for message in messages:
            out += f'\nAI: {message.content}'
        return out
