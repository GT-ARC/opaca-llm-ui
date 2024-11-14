import ast
import json
import re
import time
from typing import List, Tuple, Dict, Any

import logging

from colorama import Fore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from .llama_proxy import OpacaLLM
from ..RestGPT import build_prompt
from ..models import Response, AgentMessage
from ..opaca_proxy import proxy as opaca_proxy
from ..utils import get_reduced_action_spec, fix_parentheses, Action, openapi_to_functions, openapi_to_llama

LLAMA_SYSTEM_PROMPT_GENERATOR = """Environment:ipython
Today Date: 11 November 2024

You have access to the following functions:

{actions}

If you choose to call a function ONLY reply in the following format:
<{{start_tag}}={{function_name}}>{{parameters}}{{end_tag}}
where

start_tag => `<function`
parameters => a JSON dict with the function argument name as key and function argument value as value.
end_tag => `</function>`

Here is an example,
<function=example_function_name>{{"example_name": "example_value"}}</function>

Reminder:
- Function calls MUST follow the specified format
- Required parameters MUST be specified
- Parameter values MUST use their specified type
- Only call one function at a time
- Put the entire function call reply on one line
- If a function does not require any parameter, you still MUST output an empty JSON object like {{}}
- Sometimes you need to find parameter values first by using other functions before you can fulfill the user request

You are a helpful ai assistant."""


LLAMA_EVAL_PROMPT = """A user had the following request: {query} 
You just used the the following functions:

{functions} 

You called these functions with the following parameters: {parameters} 

The result were: {results}

Generate a response explaining the result directly to a user. DO NOT FORMULATE FUNCTION CALLS. 
At the end of your request, you must either output 
'FINISHED' if the user request has been fulfilled in its entirety and you were able to 
answer the user, or output 'CONTINUE' so more function calls can be made by another model with the newly gained information."""


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
    message_history: List = []
    should_continue: bool = True
    max_iter: int = 5
    observation_prefix = "Result: "
    llm_prefix = "Function {}: "

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
            scratchpad += (plan + "\n" + self.observation_prefix.format(i + 2) + fix_parentheses(execution_res) +
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
        used_functions = []
        c_it = 0
        self.should_continue = True
        prompt_input = message
        llm = OpacaLLM(url=self.config['llama-url'], model=self.config['llama-model'])

        # Initialize the response object
        response = Response()
        response.query = message

        try:
            actions, errors = openapi_to_llama(opaca_proxy.get_actions_with_refs(), self.config['use_agent_names'])
        except Exception as e:
            response.content = ("I am sorry, but there occurred an error during the action retrieval. "
                                "Please make sure the opaca platform is running and connected.")
            response.error = str(e)
            return response

        total_exec_time = time.time()

        messages = [SystemMessage(content=LLAMA_SYSTEM_PROMPT_GENERATOR.format(actions=actions)),
                    HumanMessage(content=prompt_input)]

        # Run until request is finished or maximum number of iterations is reached
        while self.should_continue and c_it < self.max_iter:

            llama_gen_time = time.time()
            result_gen = llm.invoke({
                'messages': messages,
                'history': self.message_history,
            })["result"]
            llama_gen_time = time.time() - llama_gen_time

            print(f'Generator output: {result_gen}')

            response.agent_messages.append(AgentMessage(
                agent="LLAMA Generator",
                content=result_gen,
                execution_time=llama_gen_time,
            ))

            match = re.search(r"<function=([a-zA-Z_][a-zA-Z0-9_\-]*)>(\{.*})</function>", result_gen)

            if match:
                action_name = match.group(1)
                parameters = json.loads(match.group(2))

                print(f'Found action "{action_name}" with parameters {parameters}')

                agent, action = action_name.split('--')
                tool_names.append(action_name)
                tool_params.append(parameters)
                used_functions.extend([action for action in actions if action["name"] == action_name])
                try:
                    tool_results.append(opaca_proxy.invoke_opaca_action(
                        action,
                        agent,
                        parameters
                    ))
                except Exception as e:
                    tool_results.append(str(e))
            else:
                return response

            llama_evl_time = time.time()
            result_evl = llm.invoke({
                "messages": [HumanMessage(
                    content=LLAMA_EVAL_PROMPT.format(
                    query=prompt_input,  # Original user query
                    functions=used_functions,  # ALL the tools used so far
                    parameters=tool_params,  # ALL the parameters used for the tools
                    results=tool_results  # ALL the results from the opaca action calls
                    ))],
                "history": []
                }
            )["result"]
            llama_evl_time = time.time() - llama_evl_time

            print(f'Evaluator Output: {result_evl}')
            response.agent_messages.append(AgentMessage(
                agent="LLAMA Evaluator",
                content=result_evl,
                execution_time=llama_evl_time,
            ))

            messages.append(AIMessage(content=result_evl))

            # Remove the keywords from the generated response
            response.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result_evl).strip()

            # Check if llm agent thinks user query has not been fulfilled yet
            if not re.search(r"\bCONTINUE\b", result_evl):
                self.should_continue = False
                return response

            c_it += 1

        response.execution_time = time.time() - total_exec_time
        return response

    async def history(self) -> list:
        return self.message_history

    async def reset(self):
        self.message_history = []

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = conf
