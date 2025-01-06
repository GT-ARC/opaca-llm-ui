from typing import Dict, Any, Tuple, List

from ..llama_proxy import OpacaLLM
from ..toolllm.tool_method import ToolMethod
from ..utils import openapi_to_llama


class ToolMethodLlama(ToolMethod):
    NAME = 'tool-llm-llama'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def get_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        tools, error = openapi_to_llama(tools_openapi, config['use_agent_names'])
        tools = [{"type": "function", "function": tool} for tool in tools]
        return tools, error

    def invoke(self):
        pass

