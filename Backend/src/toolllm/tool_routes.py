import re
import time
from typing import List

import logging
import os

from colorama import Fore
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..models import Response, AgentMessage, SessionData
from ..restgpt.utils import build_prompt
from ..utils import openapi_to_functions


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
    NAME = 'tool-llm-openai'
    llm: BaseChatModel | ChatOpenAI
    max_iter: int = 5

    async def query(self, message: str, debug: bool, api_key: str, session: SessionData) -> Response:

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        tool_responses = []
        result = None
        c_it = 0
        should_continue = True

        # Initialize the response object
        response = Response()
        response.query = message

        # Set config
        config = session.config.get(ToolLLMBackend.NAME, await self.get_config())

        # Model initialization here since openai requires api key in constructor
        try:
            self.init_model(api_key, config)
        except ValueError as e:
            response.error = str(e)
            response.content = ("You are trying to use a model which uses an api key but provided none. Please "
                                "enter a valid api key and try again.")
            return response

        try:
            # Convert openapi schema to openai function schema
            tools, error = openapi_to_functions(session.client.get_actions_with_refs(), config['use_agent_names'])
            if len(tools) > 128:
                response.error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit of "
                                   f"128. All tools after index 128 will be ignored!\n")
            if error:
                response.error += error
        except Exception as e:
            response.error += str(e)
            response.content = ("It appears no actions were returned by the Opaca Platform. Make sure you are "
                                "connected to the Opaca Runtime Platform and the platform contains at least one "
                                "action.")
            return response

        total_exec_time = time.time()

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:

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

            tool_generator_time = time.time()
            result = chain.invoke({
                'input': message,
                'scratchpad': self.build_scratchpad(tool_responses),  # scratchpad contains ai responses
                'history': session.messages
            })

            tool_generator_time = time.time() - tool_generator_time
            res_meta_data = result.response_metadata.get("token_usage", {})
            response.agent_messages.append(AgentMessage(
                agent="Tool Generator",
                content=result.content,
                response_metadata=res_meta_data,
                execution_time=tool_generator_time,
            ))

            # Check if tools were generated and if so, execute them by calling the opaca-proxy
            for call in result.tool_calls:
                tool_names.append(call['name'])
                tool_params.append(call['args'])
                try:
                    if config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    tool_results.append(
                        session.client.invoke_opaca_action(
                            action_name,
                            agent_name,
                            call['args']['requestBody'] if 'requestBody' in call['args'] else {}
                        ))
                except Exception as e:
                    tool_results.append(str(e))
                response.agent_messages[-1].tools.append(f'Tool {len(tool_names)}: '
                                                         f'{call["name"]}, '
                                                         f'{call["args"]["requestBody"] if "requestBody" in call["args"] else {} }, '
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

                tool_evaluator_time = time.time()
                result = response_chain.invoke({
                    'query': message,  # Original user query
                    'tool_names': tool_names,  # ALL the tools used so far
                    'parameters': tool_params,  # ALL the parameters used for the tools
                    'results': tool_results  # ALL the results from the opaca action calls
                })
                tool_evaluator_time = time.time() - tool_evaluator_time

                res_meta_data = result.response_metadata.get("token_usage", {})
                response.agent_messages.append(AgentMessage(
                    agent="Tool Evaluator",
                    content=result.content,
                    response_metadata=res_meta_data,
                    execution_time=tool_evaluator_time,
                ))

                # Check if llm agent thinks user query has not been fulfilled yet
                should_continue = True if re.search(r"\bCONTINUE\b", result.content) else False

                # Remove the keywords from the generated response
                result.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result.content).strip()

                # Add generated response to internal history to give result to first llm agent
                tool_responses.append(AIMessage(result.content))
            else:
                should_continue = False

            c_it += 1

        # Add query and final response to global message history
        session.messages.append(HumanMessage(message))
        session.messages.append(AIMessage(result.content))

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        return response

    @staticmethod
    async def get_config() -> dict:
        """
        Declares the default configuration
        """
        return {
            "gpt_model": "gpt-4o-mini",
            "temperature": 0,
            "use_agent_names": True,
        }

    def init_model(self, api_key: str, config: dict):
        api_key = api_key or os.getenv("OPENAI_API_KEY")  # if empty, use from Env
        self.check_for_key(api_key)
        self.llm = ChatOpenAI(
            model=config["gpt_model"],
            temperature=float(config["temperature"]),
            openai_api_key=api_key
        )

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
