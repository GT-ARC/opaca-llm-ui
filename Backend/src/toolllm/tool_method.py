import os
from abc import abstractmethod
from typing import Dict, Any, List, Tuple, Optional

from ..models import LLMAgent


class ToolMethodRegistry(type):
    registry = {}

    def __new__(cls, name, bases, attrs):
        # Create new class
        new_class = super().__new__(cls, name, bases, attrs)
        # Skip base class
        if name != "ToolMethod":
            cls.registry[attrs.get('NAME', name)] = new_class
        return new_class


class ToolMethod(metaclass=ToolMethodRegistry):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.generator_agent = None
        self.evaluator_agent = None

    @classmethod
    def create_method(cls, method_name, *args, **kwargs):
        if method_name in cls.registry:
            return cls.registry[method_name](*args, **kwargs)
        else:
            raise ValueError(f"Method {method_name} is not registered.")

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def input_variables(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def message_template(self) -> str:
        pass

    @property
    def _generator_system_prompt(self) -> str:
        return """You are a helpful ai assistant that plans solution to user queries with the help of 
                  tools. You can find those tools in the tool section. Do not generate optional 
                  parameters for those tools if the user has not explicitly told you to. 
                  Some queries require sequential calls with those tools. If other tool calls have been 
                  made already, you will receive the generated AI response of these tool calls. In that 
                  case you should continue to fulfill the user query with the additional knowledge. 
                  If you are unable to fulfill the user queries with the given tools, let the user know. 
                  You are only allowed to use those given tools. If a user asks about tools directly, 
                  answer them with the required information. Tools can also be described as services."""

    def init_agents(self, session, config):
        try:
            tools, error = self.get_tools(session.client.get_actions_with_refs(), config)
        except Exception as e:
            raise Exception(f"Unable to get tools from connected OPACA client. Are you connected with a running "
                            f"OPACA client?\nError: {e}")
        try:
            llm = self.init_model(config, session.api_key or os.environ.get("OPENAI_API_KEY"))
        except Exception as e:
            raise Exception(f"Unable to initialize model. Is a valid api key given?\n"
                            f"Error: {e}")
        self.generator_agent = LLMAgent(
            name='Tool Generator',
            llm=llm,
            system_prompt=self._generator_system_prompt,
            tools=tools,
            input_variables=self.input_variables,
            message_template=self.message_template,
        )
        self.evaluator_agent = LLMAgent(
            name="Tool Evaluator",
            llm=llm,
            system_prompt="",
            tools=tools,
            input_variables=['query', 'tool_names', 'parameters', 'results'],
            message_template="A user had the following request: {query}\n"
                             "You just used the tools {tool_names} with the following parameters: {parameters}\n"
                             "The results were {results}\n"
                             "Generate a response explaining the result to a user. Decide if the user request "
                             "requires further tools by outputting 'CONTINUE' or 'FINISHED' at the end of your "
                             "response."
        )

    @abstractmethod
    async def invoke_generator(self, session, message, tool_responses, config: Optional[Dict[str, Any]], correction_message: str = ""):
        pass

    @abstractmethod
    async def invoke_evaluator(self, message, tool_names, tool_parameters, tool_results):
        pass

    @abstractmethod
    def init_model(self, config: Dict[str, Any], api_key: str = None):
        pass

    @abstractmethod
    def get_tools(self, tools_openapi: Dict[str, Any], config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        pass

    def check_valid_action(self, calls: List[dict]) -> str:
        pass
