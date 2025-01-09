from abc import abstractmethod
from typing import Dict, Any, List, Tuple, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..models import LLMAgent, SessionData, AgentMessage


class ToolMethodRegistry(type):
    """
    A registry which stores the implemented tool methods.
    All methods inheriting from the class ToolMethod are automatically added.
    """

    registry = {}

    def __new__(cls, name, bases, attrs):
        # Create new class
        new_class = super().__new__(cls, name, bases, attrs)
        # Skip base class
        if name != "ToolMethod":
            cls.registry[attrs.get('NAME', name)] = new_class
        return new_class


class ToolMethod(metaclass=ToolMethodRegistry):
    """
    An abstract class to implement specific methods to be used in combination with the tool-method logic.
    """

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
        """
        The name of the method
        """
        pass

    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """
        A dictionary containing method specific configuration settings.
        """
        pass

    @property
    @abstractmethod
    def input_variables(self) -> List[str]:
        """
        A list of input variables, passed to the llm.
        """
        pass

    @property
    @abstractmethod
    def message_template(self) -> str:
        """
        The message template for the llm.
        """
        pass

    @property
    def _generator_system_prompt(self) -> str:
        """
        The system prompt that will be given to the generator agent.
        """
        return """You are a helpful ai assistant that plans solution to user queries with the help of 
                  tools. You can find those tools in the tool section. Do not generate optional 
                  parameters for those tools if the user has not explicitly told you to. 
                  Some queries require sequential calls with those tools. If other tool calls have been 
                  made already, you will receive the generated AI response of these tool calls. In that 
                  case you should continue to fulfill the user query with the additional knowledge. 
                  If you are unable to fulfill the user queries with the given tools, let the user know. 
                  You are only allowed to use those given tools. If a user asks about tools directly, 
                  answer them with the required information. Tools can also be described as services."""

    async def init_agents(
            self,
            session: SessionData,
            config: Dict[str, Any],
    ) -> None:
        """
        Initializes both agents (generator agent and evaluator agent).
        Needs to be called before invoking.
        :param session: The session object of the current user
        :param config: The method specific configuration
        """

        # Retrieve the tools from connected opaca platform
        # Uses the user specific opaca client
        try:
            tools, error = self.transform_tools(await session.client.get_actions_with_refs(), config)
        except Exception as e:
            raise Exception(f"Unable to get tools from connected OPACA client. Are you connected with a running "
                            f"OPACA client?\nError: {e}")

        # Initializes the method specific model
        # Optionally passes the api key for the current session
        try:
            llm = self.init_model(config, session.api_key)
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
    async def invoke_generator(
            self,
            session: SessionData,
            message: str,
            tool_responses: List[AIMessage],
            config: Optional[Dict[str, Any]],
            correction_message: str = ""
    ) -> AgentMessage:
        """
        Invokes the generator agent.
        :param session: The current session object
        :param message: The current message query sent by the user
        :param tool_responses: The list of tool responses. Per entry includes the tool name, tool parameters, tool result
        :param config: The method specific configuration
        :param correction_message: An optional correction message. Is appended to the original message
        :return: AgentMessage
        """
        pass

    @abstractmethod
    async def invoke_evaluator(
            self,
            message,
            tool_names,
            tool_parameters,
            tool_results
    ) -> AgentMessage:
        """
        Invokes the evaluator agent.
        :param message: The current message query sent by the user
        :param tool_names: A list of names of the called tools
        :param tool_parameters: A list of the parameters in JSON format of the called tools
        :param tool_results: A list of the returned results by the OPACA platform of the called tools
        :return: AgentMessage
        """
        pass

    @abstractmethod
    def init_model(
            self,
            config: Dict[str, Any],
            api_key: str = None
    ) -> BaseChatModel:
        """
        Initializes the model class.
        :param config: The method specific configuration
        :param api_key: An optional API key for the model
        """
        pass

    @abstractmethod
    def transform_tools(
            self,
            tools_openapi: Dict[str, Any],
            config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Transforms actions given as a OpenAPI specification into model specific tools.
        Also provides an additional error or warning message.
        :param tools_openapi: The list of OPACA actions in OpenAPI specification
        :param config: The method specific configuration
        :return: A list of transformed tools and an optional error/warning message
        """
        pass

    def check_valid_action(
            self,
            calls: List[dict]
    ) -> str:
        """
        A method specific tool validation method. Takes in the list of generated tool calls and compares them against
        the OPACA action definition. Returns a correction message, indicating inconsistencies, e.g. missing
        required parameters, hallucinated parameters/tool names.
        If all tool calls are valid, will return an empty string.
        :param calls: A list of generated tool calls by the model.
        :return: A correction message or an empty string.
        """
        pass
