from typing import Dict, Any, Tuple, List, Optional

from ..llama_proxy import LlamaProxy
from ..models import ConfigParameter
from ..toolllm.tool_method import ToolMethod
from ..utils import openapi_to_llama


class ToolMethodLlama(ToolMethod):
    NAME = 'tool-llm-llama'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = []

    @property
    def name(self):
        return self.NAME

    @property
    def config(self) -> Dict[str, ConfigParameter]:
        return {
                "llama-url": ConfigParameter(type="string", required=True, default="http://10.0.64.101:11000"),
                "llama-model": ConfigParameter(type="string", required=True, default="llama3.1:70b"),
                "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
                "use_agent_names": ConfigParameter(type="string", required=True, default=True),
                "max_iterations": ConfigParameter(type="string", required=True, default=5)
               }

    @property
    def input_variables(self):
        return ['input']

    @property
    def message_template(self) -> str:
        return '{input}'

    def init_model(self, config: Dict[str, Any], api_key: str = None):
        return LlamaProxy(
            url=config['llama-url'],
            model=config['llama-model']
        )

    def transform_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        tools, error = openapi_to_llama(tools_openapi, config['use_agent_names'])
        self.tools = [{"type": "function", "function": tool} for tool in tools]
        return self.tools, error

    async def invoke_generator(
            self,
            session,
            message,
            tool_responses,
            config: Optional[Dict[str, Any]],
            correction_message: str = "",
            websocket=None
    ):
        return await self.generator_agent.ainvoke({
            'input': message + correction_message,
            'config': config,
            'history': session.messages,
        })

    async def invoke_evaluator(
            self,
            message,
            tool_names,
            tool_parameters,
            tool_results,
            websocket=None
    ):
        return await self.evaluator_agent.ainvoke({
            'query': message,  # Original user query
            'tool_names': tool_names,  # ALL the tools used so far
            'parameters': tool_parameters,  # ALL the parameters used for the tools
            'results': tool_results  # ALL the results from the opaca action calls
        })

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

            # Get the parameters of the found action
            parameters = action_def.get('parameters', {})

            # Check if all required parameters are present
            if missing := [k for k, v in parameters.items() if v["required"] and k not in args.keys()]:
                err_out += f'For the function "{action}" you have not included the required parameters {missing}.\n'

            # Check if no parameter is hallucinated
            if hall := [p for p in args.keys() if p not in parameters.keys()]:
                err_out += (f'For the function "{action}" you have included the improper parameter {hall} in your '
                            f'generated list of parameters. Please only use parameters that are given in the function '
                            f'definition.\n')

        return err_out
