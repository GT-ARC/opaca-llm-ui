from typing import Dict, Any, Tuple, List, Optional

from ..llama_proxy import OpacaLLM
from ..toolllm.tool_method import ToolMethod
from ..utils import openapi_to_llama


class ToolMethodLlama(ToolMethod):
    NAME = 'tool-llm-llama'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return self.NAME

    @property
    def config(self) -> Dict[str, Any]:
        return {
                "llama-url": "http://10.0.64.101:11000",
                "llama-model": "llama3.1:70b",
                "temperature": 0,
                "use_agent_names": True,
                "max_iterations": 5
               }

    @property
    def input_variables(self):
        return ['input']

    @property
    def message_template(self) -> str:
        return '{input}'

    def init_model(self, config: Dict[str, Any], api_key: str = None):
        return OpacaLLM(
            url=config['llama-url'],
            model=config['llama-model']
        )

    def transform_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        tools, error = openapi_to_llama(tools_openapi, config['use_agent_names'])
        tools = [{"type": "function", "function": tool} for tool in tools]
        return tools, error

    async def invoke_generator(self, session, message, tool_responses, config: Optional[Dict[str, Any]], correction_message: str = ""):
        return await self.generator_agent.ainvoke({
            'input': message + correction_message,
            'config': config,
            'history': session.messages,
        })

    async def invoke_evaluator(self, message, tool_names, tool_parameters, tool_results):
        return await self.evaluator_agent.ainvoke({
            'query': message,  # Original user query
            'tool_names': tool_names,  # ALL the tools used so far
            'parameters': tool_parameters,  # ALL the parameters used for the tools
            'results': tool_results  # ALL the results from the opaca action calls
        })
