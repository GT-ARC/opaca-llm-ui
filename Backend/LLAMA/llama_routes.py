import json
import re
import time
from typing import List, Dict, Any

import logging

from colorama import Fore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .llama_proxy import OpacaLLM
from ..models import Response, AgentMessage
from ..opaca_proxy import proxy as opaca_proxy
from ..utils import openapi_to_llama

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

You called these functions with the following parameters: 

{parameters} 

The results were: 

{results}

Generate a response explaining the results directly to a user. DO NOT FORMULATE FUNCTION CALLS. 
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
    message_history: List = []          # Messages generated in previous iterations
    max_iter: int = 5                   # Maximum number of internal iterations

    def __init__(self):
        # This is the DEFAULT config
        self.config = {
            "llama-url": "http://10.0.64.101:11000",
            "llama-model": "llama3.1:70b",
            "temperature": 0,
            "use_agent_names": True,
            "max_iterations": 5
        }

    @staticmethod
    def _fix_type(action: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given the correct action definition, iterates through the list of generated parameters
        and checks if the parameter types matches the type in the definition. If it does not,
        this function attempts to cast the generated value to the expected value.
        :param action: Reference definition of the OPACA action
        :param parameters: Generated parameter list by the LLM
        :return: The parameter list with potential type fixes
        """
        out = parameters
        for key, value in parameters.items():
            for a_key in action.get("parameters", {}).keys():
                print(f'Key: {a_key}')
                try:
                    if key == a_key:
                        print(f'type: {action["parameters"][a_key]["param_type"]}')
                        match action["parameters"][a_key]["param_type"]:
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
                except ValueError:
                    # This is pretty ugly
                    # The idea is that if an invalid value was found, it should not try to cast this value but skip it
                    # The Evaluator will then receive the error encountered during the action invocation
                    continue
        return out

    async def query(self, message: str, debug: bool, api_key: str) -> Response:

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        c_it = 0
        should_continue = True
        prompt_input = message
        llm = OpacaLLM(url=self.config['llama-url'], model=self.config['llama-model'])

        # Initialize the response object
        response = Response()
        response.query = message

        # Save time before execution
        total_exec_time = time.time()

        # Get list of available actions from connected opaca platform
        try:
            actions, errors = openapi_to_llama(opaca_proxy.get_actions_with_refs(), self.config['use_agent_names'])
        except Exception as e:
            response.content = ("I am sorry, but there occurred an error during the action retrieval. "
                                "Please make sure the OPACA platform is running and connected.")
            response.error = str(e)
            return response

        # Save system message and user input in list of messages
        # This list only saves the generated messages of the current iteration
        messages = [SystemMessage(content=LLAMA_SYSTEM_PROMPT_GENERATOR.format(actions=actions)),
                    HumanMessage(content=prompt_input)]

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:

            # Invoke the GENERATOR
            # Attempts to generate a function call for the current user request
            llama_gen_time = time.time()
            result_gen = llm.invoke({
                'messages': messages,
                'history': self.message_history,
                'config': self.config,
            })["result"]
            llama_gen_time = time.time() - llama_gen_time

            # Save the result in the list of internal messages
            messages.append(AIMessage(content=result_gen))
            print(f'Generator output: {result_gen}')

            response.agent_messages.append(AgentMessage(
                agent="LLAMA Generator",
                content=result_gen,
                execution_time=llama_gen_time,
            ))

            # Check if a function was generated
            match = re.search(r"<function=([a-zA-Z_][a-zA-Z0-9_\-]*)>(\{.*})</function>", result_gen)

            # If a function was generated, try to retrieve the action name and the parameters
            if match:
                action_name = match.group(1)
                parameters = json.loads(match.group(2))
                print(f'Found action "{action_name}" with parameters {parameters}')
                agent, action = action_name.split('--')
                tool_names.append(action_name)

                # Fix the parameter types based on the action definition
                used_function = {}
                for a in actions:
                    if a["name"] == action_name:
                        used_function = a
                parameters = self._fix_type(used_function, parameters)
                tool_params.append(parameters)

                # Attempt to invoke the generated action call
                # Save the result (or error) in the results
                try:
                    tool_results.append(opaca_proxy.invoke_opaca_action(
                        action,
                        agent,
                        parameters
                    ))
                except Exception as e:
                    tool_results.append(str(e))

                # Append the generated tool to the last agent message (the last Generator message)
                response.agent_messages[-1].tools.append(f'Tool {len(tool_names)}: '
                                                         f'{tool_names[-1]}, '
                                                         f'{tool_params[-1]}, '
                                                         f'{tool_results[-1]}\n')
            else:
                # If no function was generated, save the result and return the response directly
                self.message_history.append({"role": "user", "content": prompt_input})
                self.message_history.append({"role": "assistant", "content": response.content})
                return response

            # Evaluate the original user request against the achieved results so far
            # Only considers generated messages in this iteration
            llama_evl_time = time.time()
            result_evl = llm.invoke({
                "messages": [HumanMessage(
                    content=LLAMA_EVAL_PROMPT.format(
                        query=prompt_input,  # Original user query
                        functions=tool_names,  # ALL the tools used so far
                        parameters=tool_params,  # ALL the parameters used for the tools
                        results=tool_results  # ALL the results from the opaca action calls
                    ))],
                "history": [],
                "config": self.config,
                }
            )["result"]
            llama_evl_time = time.time() - llama_evl_time

            # Add the Evaluator message to the list of agent messages
            # and the internal list of messages
            response.agent_messages.append(AgentMessage(
                agent="LLAMA Evaluator",
                content=result_evl,
                execution_time=llama_evl_time,
            ))
            print(f'Evaluator Output: {result_evl}')
            messages.append(HumanMessage(content=result_evl))

            # Remove the keywords from the generated response
            response.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result_evl).strip()

            # Check if the evaluator thinks the user query has not been fulfilled yet
            if not re.search(r"\bCONTINUE\b", result_evl):
                should_continue = False
            c_it += 1

        # Save the total execution time and the messages in the global history and return the response
        response.execution_time = time.time() - total_exec_time
        self.message_history.append({"role": "user", "content": prompt_input})
        self.message_history.append({"role": "assistant", "content": response.content})
        return response

    async def history(self) -> list:
        return self.message_history

    async def reset(self):
        self.message_history = []

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = conf
