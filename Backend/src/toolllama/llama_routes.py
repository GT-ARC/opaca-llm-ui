import json
import re
import time
from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ..llama_proxy import LlamaProxy
from ..models import Response, AgentMessage, SessionData, OpacaLLMBackend, ConfigParameter
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
- If a user asks about your functionality, give a summary of your provided functions
- If a user has a question about a specific function, answer them directly

You are a helpful ai assistant."""


LLAMA_EVAL_PROMPT = """A user had the following request: {query} 
You just used the the following functions:

{functions} 

You called these functions with the following parameters: 

{parameters} 

The results were: 

{results}

Generate a response explaining the results directly to a user. DO NOT FORMULATE FUNCTION CALLS. 
Please note that the results are in order, meaning that an error might have been resolved by a later result.
At the end of your request, you must either output 
'FINISHED' if the user request has been fulfilled in its entirety and you are able to answer the user, 
or output 'CONTINUE' so more function calls can be made by another model with the newly gained information. 
Base your final decision of whether the query has been fulfilled only on the presence of information. For example, if 
a user asked if devices are damaged and it was found out they are, the query is fulfilled. If you think the last 
function call included errors, for example an incorrect data type, you should hint at these errors in your response."""


class LLamaBackend(OpacaLLMBackend):
    max_iter: int = 5                   # Maximum number of internal iterations
    NAME = "tool-llm-llama"

    @property
    def config_schema(self) -> dict:
        """
        Declares the default configuration
        """
        return {
                "llama-url": ConfigParameter(type="string", required=True, default="http://10.0.64.101:11000"),
                "llama-model": ConfigParameter(type="string", required=True, default="llama3.1:70b"),
                "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
                "use_agent_names": ConfigParameter(type="string", required=True, default=True),
                "max_iterations": ConfigParameter(type="string", required=True, default=5)
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
                try:
                    if key == a_key:
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

    async def query(self, message: str, session: SessionData) -> Response:

        # Set the config
        config = session.config.get(LLamaBackend.NAME, self.default_config())

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        c_it = 0
        should_continue = True
        prompt_input = message
        llm = LlamaProxy(url=config['llama-url'], model=config['llama-model'])

        # Initialize the response object
        response = Response()
        response.query = message

        # Save time before execution
        total_exec_time = time.time()

        # Get list of available actions from connected opaca platform
        try:
            actions, errors = openapi_to_llama(await session.client.get_actions_with_refs(), config['use_agent_names'])
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
            result_gen = await llm.ainvoke({
                'messages': messages,
                'history': session.messages,
                'config': config,
                'tools': [],
            })
            llama_gen_time = time.time() - llama_gen_time

            # Save the result in the list of internal messages
            messages.append(result_gen)
            print(f'Generator output: {result_gen.content}')

            response.agent_messages.append(AgentMessage(
                agent="Tool Generator",
                content=result_gen.content,
                execution_time=llama_gen_time,
            ))

            # Check if a function was generated
            match = re.search(r"<function=([a-zA-Z_][a-zA-Z0-9_\-]*)>(\{.*})</function>", result_gen.content)

            # If a function was generated, try to retrieve the action name and the parameters
            if match:
                action_name = match.group(1)
                parameters = json.loads(match.group(2))
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
                    tool_results.append(await session.client.invoke_opaca_action(
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
                response.content = result_gen.content
                response.execution_time = time.time() - total_exec_time
                response.iterations = c_it + 1
                session.messages.append(HumanMessage(prompt_input))
                session.messages.append(AIMessage(response.content))
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
                "config": config,
                "tools": []
                }
            )
            llama_evl_time = time.time() - llama_evl_time

            # Add the Evaluator message to the list of agent messages
            # and the internal list of messages
            response.agent_messages.append(AgentMessage(
                agent="Tool Evaluator",
                content=result_evl.content,
                execution_time=llama_evl_time,
            ))
            print(f'Evaluator Output: {result_evl.content}')
            messages.append(HumanMessage(content=result_evl.content))

            # Remove the keywords from the generated response
            response.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result_evl.content).strip()

            # Check if the evaluator thinks the user query has not been fulfilled yet
            if not re.search(r"\bCONTINUE\b", result_evl.content):
                should_continue = False
            c_it += 1

        # Save the total execution time and the messages in the global history and return the response
        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it + 1
        session.messages.append(HumanMessage(prompt_input))
        session.messages.append(AIMessage(response.content))
        return response
