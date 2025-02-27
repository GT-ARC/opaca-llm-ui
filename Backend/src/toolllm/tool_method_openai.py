import os
from typing import Dict, Any, List, Tuple, Optional

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..models import ConfigParameter
from ..toolllm.tool_method import ToolMethod
from ..utils import openapi_to_functions


class ToolMethodOpenAI(ToolMethod):
    NAME = 'tool-llm'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []

    @property
    def name(self):
        return self.NAME
    
    @property
    def config(self) -> Dict[str, ConfigParameter]:
        return {
                "model": ConfigParameter(type="string", required=True, default='gpt-4o-mini'),
                "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
                "use_agent_names": ConfigParameter(type="boolean", required=True, default=True),
               }

    @property
    def input_variables(self):
        return ['input', 'scratchpad']

    @property
    def message_template(self) -> str:
        return 'Human: {input}{scratchpad}'

    def init_model(self, config: Dict[str, Any], api_key: str = None):
        if config["model"].startswith("gpt"):
            key = api_key or os.getenv("OPENAI_API_KEY")
            base_url = None
        else:
            # If model does NOT start with gpt: use vllm
            key = os.getenv("VLLM_API_KEY")
            base_url = os.getenv("VLLM_BASE_URL")
        return ChatOpenAI(
            model=config["model"],
            temperature=float(config["temperature"]),
            openai_api_key=key,
            openai_api_base=base_url
        )

    def transform_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        # Convert openapi schema to openai function schema
        self.tools, error = openapi_to_functions(tools_openapi, config['use_agent_names'])
        if len(self.tools) > 128:
            self.tools = self.tools[:128]
            error += (f"WARNING: Your number of tools ({len(self.tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
        return self.tools, error

    async def invoke_generator(self, session, message, tool_responses, config: Optional[Dict[str, Any]], correction_messages: str = "", websocket=None):
        # VLLM has problems streaming tool outputs, disable streaming for vllm models
        if config["model"].startswith("gpt"):
            result = await self.generator_agent.ainvoke({
                'input': message,
                'scratchpad': self.build_scratchpad(tool_responses) + correction_messages,  # scratchpad contains ai responses
                'history': session.messages
            }, websocket)
        else:
            result = self.generator_agent.invoke({
                'input': message,
                'scratchpad': self.build_scratchpad(tool_responses) + correction_messages,
                # scratchpad contains ai responses
                'history': session.messages
            })

        for action in result.tools:
            # Fix the parameter types based on the action definition
            used_function = {}
            for a in self.tools:
                if a["function"]["name"] == action["name"]:
                    used_function = a["function"]
            parameters = self._fix_type(used_function.get("parameters", {}).get("properties", {}).get("requestBody", {}).get("properties", {}), action["args"].get("requestBody", {}))
            action["args"]["requestBody"] = parameters

        return result

    async def invoke_evaluator(self, message, tool_names, tool_params, tool_results, websocket=None):
        return await self.evaluator_agent.ainvoke({
            'query': message,  # Original user query
            'tool_names': tool_names,  # ALL the tools used so far
            'parameters': tool_params,  # ALL the parameters used for the tools
            'results': tool_results  # ALL the results from the opaca action calls
        }, websocket)

    @staticmethod
    def build_scratchpad(messages: List[AIMessage]) -> str:
        out = ''
        for message in messages:
            out += f'\nAI: {message.content}'
        return out

    def check_valid_action(self, calls: List[dict]) -> str:
        # Save all encountered errors in a single string, which will be given to the llm as an input
        err_out = ""

        # Since the gpt models can generate multiple tools, iterate over each generated call
        for call in calls:

            # Get the generated name and parameters
            action = call['name']
            args = call['args'].get('requestBody', {})

            # Check if the generated action name is found in the list of action definitions
            # If not, abort current iteration since no reference parameters can be found
            action_def = None
            for a in self.tools:
                if a['function']['name'] == action:
                    action_def = a['function']
            if not action_def:
                err_out += (f'Your generated function name "{action}" does not exist. Only use the exact function name '
                            f'defined in your tool section. Please make sure to separate the agent name and function '
                            f'name with two hyphens "--" if it is defined that way.\n')
                continue

            # Get the request body definition of the found action
            req_body = action_def['parameters']['properties'].get('requestBody', {})

            # Check if the generated parameters are in the right place (in the requestBody field) if the generated
            # action requires at least one parameter
            # If not, abort current iteration since we have to assume no parameters were generated at all
            if req_body.get('required', []) and not args:
                err_out += (f'For the function "{action}" you have not included any parameters in the request body, '
                            f'even though the function requires certain parameters. Please make sure to always put '
                            f'your generated parameters in the request body field.\n')
                continue

            # Check if all required parameters are present
            if missing := [p for p in req_body.get('required', []) if p not in args.keys()]:
                err_out += f'For the function "{action}" you have not included the required parameters {missing}.\n'

            # Check if no parameter is hallucinated
            if hall := [p for p in args.keys() if p not in req_body.get('properties', {}).keys()]:
                err_out += (f'For the function "{action}" you have included the improper parameter {hall} in your '
                            f'generated list of parameters. Please only use parameters that are given in the function '
                            f'definition.\n')

        return err_out

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
            for a_key in action.keys():
                try:
                    if key == a_key:
                        match action[a_key]["type"]:
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
                except Exception as e:
                    # This is pretty ugly
                    # The idea is that if an invalid value was found, it should not try to cast this value but skip it
                    # The Evaluator will then receive the error encountered during the action invocation
                    print(e)
                    continue
        return out
