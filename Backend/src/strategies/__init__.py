from .simple import SimpleMethod
from .simple_tools import SimpleToolsMethod
from .toolllm import ToolLLMMethod
from .orchestrated import SelfOrchestratedMethod
from .abstract_method import AbstractMethod

# all Strategies by name
METHODS = {
    SimpleMethod.NAME: SimpleMethod,
    SimpleToolsMethod.NAME: SimpleToolsMethod,
    ToolLLMMethod.NAME: ToolLLMMethod,
    SelfOrchestratedMethod.NAME: SelfOrchestratedMethod,
}

# basic simple tool-calling method as default
DEFAULT_METHOD = SimpleToolsMethod
