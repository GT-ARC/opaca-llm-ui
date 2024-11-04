import ast
import json
import re
import time
from typing import List, Tuple, Dict, Any

import logging

from colorama import Fore
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate

from .llama_proxy import OpacaLLM
from ..models import Response, AgentMessage
from ..opaca_proxy import proxy as opaca_proxy
from ..utils import get_reduced_action_spec, fix_parentheses, Action

LLAMA_PROMPT = """You are a helpful ai assistant that plans solution to user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to.
Some queries require sequential calls with those tools. Never output tool calls missing information. If possible, 
generate the tool calls to get that information first. For example, if a tool requires an id to a given value and the 
user has provided you with the value, check if a tool exist to get the associated id. If other tool calls have been 
made already, you will receive the generated AI response of these tool calls. In that 
case you should continue to fulfill the user query with the additional knowledge. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services.

Always generate tool calls the following format:

{{"name": "tool", "parameters": {{"parameter_name": value}}}}

Do NOT generate multiple tool calls. Instead use the next Plan step to generate the next one if necessary.
Make sure you format the value of the parameters correctly. If a value should be an integer or number, do not use 
quotation marks or apostrophes around the value. Do not capitalize the keys. Always put the keys in quotation marks. Use the exact parameter names given in the tool definitions.
Always use the full name of a tool. Do not use tool names as parameter values.

A typical conversation where a user wants you to use tools will look like this:

User query: The input from the user
Plan step 1: The first step of your plan.
API response: This is the result of your first plan step.
Plan step 2: The second step of your plan.
API response: This the the result of your second plan step.
... (this Plan step n and API response can repeat N times)

Here is the list of tools you use to formulate your steps:

{actions}

Begin!

User query: {input}
Plan step 1: {scratchpad}
"""

LLAMA_PROMPT_ALT = """Given the following functions, please respond with a JSON for a function call with it proper 
arguments that best answers the given prompt. 

Respond in the format {{"name": "function name", "parameters": dictionary of argument names and its value}}. 
Do not use variables.

It can happen that a user task requires multiple, sequential function call. For that case, only output the next 
concrete step of your proposed plan in the following format:

User query: The input from the user
Plan step 1: The first step of your plan.
API response: This is the result of your first plan step.
Plan step 2: The second step of your plan.
API response: This the the result of your second plan step.
... (this Plan step n and API response can repeat N times)

Here is the list of functions: 

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
                           "\n" + self.llm_prefix.format(i + 2))
        print(f'Scratchpad built: {scratchpad}')
        return scratchpad

    def _check_for_tools(self, message: str) -> List:
        tools = []
        if re.search(r"python_tag", message):
            for tool in re.sub(r'<\|python_tag\|>', '', message).strip().split(';'):
                try:
                    tools.append(json.loads(tool))
                except ValueError:
                    print(f'Tool could not get converted: {tool}')
                    continue
        else:
            try:
                for tool in message.split(';'):
                    tools.append(json.loads(tool))
            except ValueError:
                print(f'Message is no tool call: {message}')
        return tools

    def _fix_type(self, action: Action, parameters: Dict[str, Any]):
        out = parameters
        for key, value in parameters.items():
            for a_key in action.params_in.keys():
                print(f'Key: {a_key}')
                if key == a_key:
                    print(f'type: {action.params_in[a_key].type}')
                    match action.params_in[a_key].type:
                        case 'string':
                            out[key] = str(value)
                        case 'number':
                            out[key] = float(value)
                        case 'integer':
                            out[key] = int(value)
                        case 'boolean':
                            out[key] = bool(value)
                        case _:
                            out[key] = value
        return out


    async def query(self, message: str, debug: bool, api_key: str) -> Response:

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        tool_responses = []
        history = []
        c_it = 0
        self.should_continue = True
        prompt_input = message
        llm = OpacaLLM(url=self.config['llama-url'], model=self.config['llama-model'])

        # Initialize the response object
        response = Response()
        response.query = message

        try:
            actions = get_reduced_action_spec(opaca_proxy.get_actions_with_refs())
            action_list = [action.llama_str(self.config['use_agent_names']) for action in actions]
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
                template=LLAMA_PROMPT_ALT,
                partial_variables={"actions": action_list, "scratchpad": self._construct_scratchpad(history)},
                input_variables=["input"]
            )

            chain = prompt | llm

            llama_gen_time = time.time()
            result_gen = chain.invoke({
                'input': prompt_input,
                #'history': self.messages
            })["result"]
            llama_gen_time = time.time() - llama_gen_time


            print(f'Generator Output: {result_gen}')

            response.agent_messages.append(AgentMessage(
                agent="LLAMA Generator",
                content=result_gen,
                execution_time=llama_gen_time,
            ))
            response.content = result_gen

            tools = self._check_for_tools(result_gen)
            print(f'Found tools: {tools}')

            for call in tools:
                tool_names.append(call['name'])
                tool_params.append(call['parameters'])
                try:
                    if self.config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']

                    params = call.get('parameters', {})
                    print(f'Params before: {params}')
                    for action in actions:
                        if action.action_name == action_name:
                            params = self._fix_type(action, call['parameters'])
                    print(f'Params built: {params}')

                    tool_results.append(
                        opaca_proxy.invoke_opaca_action(
                            action_name,
                            agent_name,
                            params,
                        ))
                except Exception as e:
                    print(f'ERROR: {str(e)}')
                    tool_results.append(str(e))
                response.agent_messages[-1].tools.append(f'Tool {len(tool_names)}: '
                                                         f'{call["name"]}, '
                                                         f'{call.get("parameters", {})}, '
                                                         f'{tool_results[-1]}\n')
            if tools:
                prompt_template = PromptTemplate(
                    template="A user had the following request: {query}\n"
                             "You just used the tools {tool_names} with the following parameters: {parameters}\n"
                             "The results were {results}\n"
                             "Generate a response explaining the result to a user. At the end of your request, output "
                             "'FINISHED' the user request has been fulfilled in its entirety and you were able to "
                             "answer the user, or output 'CONTINUE' so more tool calls can be made.",
                    input_variables=['query', 'tool_names', 'parameters', 'results'],
                )
                response_chain = prompt_template | llm

                tool_evaluator_time = time.time()
                result_evl = response_chain.invoke({
                    'query': message,  # Original user query
                    'tool_names': tool_names,  # ALL the tools used so far
                    'parameters': tool_params,  # ALL the parameters used for the tools
                    'results': tool_results  # ALL the results from the opaca action calls
                })["result"]

                print(f'Evaluator Output: {result_evl}')

                tool_evaluator_time = time.time() - tool_evaluator_time
                response.agent_messages.append(AgentMessage(
                    agent="LLAMA Evaluator",
                    content=result_evl,
                    execution_time=tool_evaluator_time,
                ))

                # Check if llm agent thinks user query has not been fulfilled yet
                self.should_continue = True if re.search(r"\bCONTINUE\b", result_evl) else False

                # Remove the keywords from the generated response
                response.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result_evl).strip()

                history.append((result_gen, result_evl))
            else:
                self.should_continue = False
            c_it += 1

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
