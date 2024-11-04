import ast
import json
import re
import time
from typing import List, Tuple

import logging

from colorama import Fore
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate

from .llama_proxy import OpacaLLM
from ..models import Response, AgentMessage
from ..opaca_proxy import proxy as opaca_proxy
from ..utils import get_reduced_action_spec, fix_parentheses

LLAMA_PROMPT = """You plan solutions to user queries. A user will give you a question or instruction and you will output the next 
concrete step to solve this question or instruction. You will receive a list of available actions, some of which will 
include descriptions. You use these actions to formulate the steps. Some user queries can only be fulfilled with 
multiple steps. Sometimes to fulfill a query you need additional information, which can be retrieved by available 
actions. For example, if a query requires you to book a free desk, you first need to output a step to check if a given 
desk is free. Some actions will require parameters to be called. Always use the most fitting value from the user query 
as parameters in your steps. Make the value you want to use for a parameter very clear.
If you are certain the user has not provided you with all required parameters for service you want to call and you are 
unable to retrieve those parameters with actions, output the keyword "STOP" and ask the user for the remaining required parameters.
Once you receive a useful response for your step, continue with the next step.
If the user asks about more information about specific services or actions, you put the 
keyword "STOP" in front of your reply and answer the user directly. 
Never put the keyword "STOP" in your reply when your reply indicates that a service should be called.

You are allowed to use tools. If you do, please format them accordingly in the following format:

{{"Name": "ToolName", "Parameters": {{"ParameterName": ParameterValue}}}}

If you have generated multiple tool calls, output them separated with a semicolon.

A typical conversation where a user wants you to call services will look like this:

User query: The input from the user
Plan step 1: The first step of your plan.
API response: This is the result of your first plan step.
Plan step 2: The second step of your plan.
API response: This the the result of your second plan step.
... (this Plan step n and API response can repeat N times)

Here is the list of services you use to formulate your steps:

{actions}

Begin!

User query: {input}
Plan step 1: {scratchpad}
"""


class ColorPrint:
    def __init__(self):
        self.color_mapping = {
            "Generator": Fore.RED,
            "Evaluator": Fore.GREEN,
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


class LLamaBackend:
    messages: List = []
    should_continue: bool = True
    max_iter: int = 5
    observation_prefix = "API Response: "
    llm_prefix = "Plan Step {}: "

    def __init__(self):
        # This is the DEFAULT config
        self.config = {
            "llama-url": "http://10.0.64.101:11000",
            "llama-model": "llama3.1:70b",
            "temperature": 0,
            "use_agent_names": True,
            "max_iterations": 5
        }

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]]
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, execution_res) in enumerate(history):
            scratchpad += (plan + "\n" + self.observation_prefix + fix_parentheses(execution_res) +
                           "\n" + self.llm_prefix.format(i + 1))
        return scratchpad

    def _check_for_tools(self, message: str) -> List:
        tools = []
        if re.search(r"python_tag", message):
            for tool in re.sub(r'<\|python_tag\|>', '', message).strip().split(';'):
                try:
                    ast.literal_eval(tool)
                    tools.append(tool)
                except ValueError:
                    print(f'Tool could not get converted: {tool}')
                    continue
        return tools

    async def query(self, message: str, debug: bool, api_key: str) -> Response:

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        tool_responses = []
        history = []
        result = None
        c_it = 0
        self.should_continue = True
        prompt_input = message
        llm = OpacaLLM(url=self.config['llama-url'], model=self.config['llama-model'])

        # Initialize the response object
        response = Response()
        response.query = message

        try:
            actions = get_reduced_action_spec(opaca_proxy.get_actions_with_refs())
            action_list = ""
            for action in actions:
                action_list += action.planner_str(self.config['use_agent_names']) + '\n'
        except Exception as e:
            response.content = ("I am sorry, but there occurred an error during the action retrieval. "
                                "Please make sure the opaca platform is running and connected.")
            response.error = str(e)
            return response

        total_exec_time = time.time()

        # Run until request is finished or maximum number of iterations is reached
        while self.should_continue and c_it < self.max_iter:

            # Build first llm agent
            prompt = PromptTemplate(
                template=LLAMA_PROMPT,
                partial_variables={"actions": action_list, "scratchpad": self._construct_scratchpad(history)},
                input_variables=["input"]
            )

            chain = prompt | llm

            llama_gen_time = time.time()
            result = chain.invoke({
                'input': prompt_input,
                #'history': self.messages
            })["result"]
            llama_gen_time = time.time() - llama_gen_time


            print(f'Generator Output: {result}')

            response.agent_messages.append(AgentMessage(
                agent="LLAMA Generator",
                content=result,
                execution_time=llama_gen_time,
            ))

            tools = self._check_for_tools(result)

            print(f'Found tools: {tools}')

            return response

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

                tool_evaluator_time = time.time() - tool_generator_time
                res_meta_data = result.response_metadata.get("token_usage", {})
                response.agent_messages.append(AgentMessage(
                    agent="Tool Evaluator",
                    content=result.content,
                    response_metadata=res_meta_data,
                    execution_time=tool_evaluator_time,
                ))

                # Check if llm agent thinks user query has not been fulfilled yet
                self.should_continue = True if re.search(r"\bCONTINUE\b", result.content) else False

                # Remove the keywords from the generated response
                result.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result.content).strip()

                # Add generated response to internal history to give result to first llm agent
                tool_responses.append(AIMessage(result.content))
            else:
                self.should_continue = False

            c_it += 1

        # Add query and final response to global message history
        self.messages.append(HumanMessage(message))
        self.messages.append(AIMessage(result.content))

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        return response

    async def history(self) -> list:
        return self.messages

    async def reset(self):
        self.messages = []

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = conf

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
