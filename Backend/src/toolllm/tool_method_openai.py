from typing import Dict, Any, List, Tuple

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..toolllm.tool_method import ToolMethod
from ..utils import openapi_to_functions


class ToolMethodOpenAI(ToolMethod):
    NAME = 'tool-llm-openai'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []

    @property
    def name (self):
        return self.NAME
    
    @property
    def config(self) -> Dict[str, Any]:
        return {
                "gpt_model": "gpt-4o-mini",
                "temperature": 0,
                "use_agent_names": True,
               }

    @property
    def input_variables(self):
        return ['input', 'scratchpad']

    @property
    def message_template(self) -> str:
        return 'Human: {input}{scratchpad}'

    def init_model(self, config: Dict[str, Any], api_key: str = None):
        return ChatOpenAI(
            model=config["gpt_model"],
            temperature=float(config["temperature"]),
            openai_api_key=api_key
        )

    def get_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        print(f'config in tool openai: {config}')
        # Convert openapi schema to openai function schema
        self.tools, error = openapi_to_functions(tools_openapi, config['use_agent_names'])
        if len(self.tools) > 128:
            self.tools = self.tools[:128]
            error += (f"WARNING: Your number of tools ({len(self.tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
        return self.tools, error

    def invoke_generator(self, session, message, tool_responses, correction_messages: str = ""):
        return self.generator_agent.invoke({
            'input': message,
            'scratchpad': self.build_scratchpad(tool_responses) + correction_messages,  # scratchpad contains ai responses
            'history': session.messages
        })

    def invoke_evaluator(self, message, tool_names, tool_params, tool_results):
        return self.evaluator_agent.invoke({
            'query': message,  # Original user query
            'tool_names': tool_names,  # ALL the tools used so far
            'parameters': tool_params,  # ALL the parameters used for the tools
            'results': tool_results  # ALL the results from the opaca action calls
        })

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
