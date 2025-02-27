"""
Request and response models used in the FastAPI routes (and in some of the implementations).
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Self
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, SystemMessage
from langchain_core.outputs import GenerationChunk, ChatGenerationChunk
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate, \
    FewShotChatMessagePromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, field_validator, model_validator, Field
from starlette.websockets import WebSocket


class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter that logs output colorful
    """

    # Define agent-specific colors
    AGENT_COLORS = {
        # Rest-GPT
        "Planner": "\x1b[31;1m",  # Bright Red
        "Action Selector": "\x1b[33;1m",  # Bright Yellow
        "Caller": "\x1b[34;1m",  # Bright Blue
        "Evaluator": "\x1b[32;1m",  # Bright Green

        # Tool-llm
        "Tool Generator": "\x1b[31;20m",  # Dim Red
        "Tool Evaluator": "\x1b[33;20m",  # Dim Yellow

        # Simple Roles
        "system": "\x1b[93m",  # Light Yellow
        "assistant": "\x1b[94m",  # Light Blue
        "user": "\x1b[97m",  # Light White

        # Default
        "Default": "\x1b[38;20m",  # Dim White
    }

    def format(self, record):
        agent_name = getattr(record, "agent_name", "Default")
        color = self.AGENT_COLORS.get(agent_name, self.AGENT_COLORS["Default"])

        # Get formatted timestamp
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Indent multi-line messages
        message = record.getMessage().replace("\n", f"\n{' ' * (len(timestamp) + len(agent_name) + len(record.levelname) + 7)}")

        # Format log entry
        log_entry = f"{timestamp} [{record.levelname}] {agent_name} - {message.strip()}"

        return f"{color}{log_entry}\x1b[0m"


# Define a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)


class Url(BaseModel):
    url: str
    user: str | None
    pwd: str | None


class Message(BaseModel):
    user_query: str
    api_key: str = ""


class AgentMessage(BaseModel):
    """
    Stores individual information generated by the various agents
    """
    agent: str
    content: str = ''
    tools: List[Dict[str, Any]] = []
    response_metadata: Dict[str, Any] = {}
    execution_time: float = .0
    status: str = Field(default="", description="Status of the agent's execution (e.g., 'Planning', 'Executing', 'Completed')")
    step: str = Field(default="", description="Current step being executed")


class Response(BaseModel):
    """
    Stores relevant information that have been generated by the backends
    """
    query: str = ''
    agent_messages: List[AgentMessage] = []
    iterations: int = 0
    execution_time: float = .0
    content: str = ''
    error: str = ''


class SessionData(BaseModel):
    """
    Stores relevant information regarding the session
    """
    messages: List[Any] = []
    config: Dict[str, Any] = {}
    client: Any = None
    api_key: str = None


class ConfigArrayItem(BaseModel):
    type: str
    array_items: 'Optional[ConfigArrayItem]' = None

class ConfigParameter(BaseModel):
    """
    A custom parameter definition for the configuration of each implemented method
    Valid types are ["integer", "number", "string", "boolean", "array", "object", "null"]
    """
    type: str
    required: bool
    default: Any
    array_items: Optional[ConfigArrayItem] = None
    description: Optional[str] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    enum: Optional[List[Any]] = None

    @model_validator(mode='after')
    def validate_after(self: Self) -> Self:
        if self.type == 'array' and self.array_items is None:
            raise ValueError(f'ConfigParameter.array_items cannot be "None" if ConfigParameter.type is "array"')
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError(f'ConfigParameter.maximum has to be larger than ConfigParameter.minimum')
        if self.enum is not None and self.default not in self.enum:
            raise ValueError(f'ConfigParameter.default must be one of {self.enum}')
        if (self.minimum is not None or self.maximum is not None) and self.type not in ["integer", "number"]:
            raise ValueError(f'The fields minimum and maximum can only be set for the types "integer" or "number".')
        return self

    # noinspection PyNestedDecorators
    @field_validator('type', mode='after')
    @classmethod
    def type_validator(cls, value: str) -> str:
        if value not in ["integer", "number", "string", "boolean", "array", "object", "null"]:
            raise ValueError(f'Value type "{value}" is not valid')
        return value


class ConfigPayload(BaseModel):
    value: Any
    config_schema: Dict[str, ConfigParameter]          # just 'schema' would shadow parent attribute in BaseModel


class OpacaLLMBackend(ABC):
    NAME: str
    llm: BaseChatModel

    @property
    @abstractmethod
    def config_schema(self) -> Dict[str, ConfigParameter]:
        pass

    def default_config(self):
        def extract_defaults(schema):
            # Extracts the default values of nested configurations
            if isinstance(schema, ConfigParameter):
                if schema.type == 'object' and isinstance(schema.default, dict):
                    return {key: extract_defaults(value) for key, value in schema.default.items()}
                else:
                    return schema.default
            else:
                return schema
        return {key: extract_defaults(value) for key, value in self.config_schema.items()}

    @abstractmethod
    async def query(self, message: str, session: SessionData) -> Response:
        pass

    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        pass


class StreamCallbackHandler(BaseCallbackHandler):

    def __init__(self, agent_message: AgentMessage, websocket):
        self.agent_message = agent_message
        self.websocket = websocket
        self.tool_calls = None
        self.first = True

    async def on_llm_new_token(
            self,
            token: str,
            *,
            chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> Any:
        """
        Is called everytime the llm generates a new token.
        If the handler was initialized with a websocket, sends an incomplete AgentMessage via the websocket.
        The generated AgentMessage does NOT include the result from the OPACA platform.
        Generated tools are "extended" over time and send as a list.
            E.g.: 1st event: [{"name": "foo", "args": {}}]
                  2nd event: [{"name": "foo", "args": {"param": "value"}}]
                  ...
        Generated output tokens are send on their own in the content field.
            E.g.: 1st event: "Hello"
                  2nd event: " World"
                  ...
        """
        if chunk.message.additional_kwargs.get('tool_calls', {}):
            if self.first:
                self.tool_calls = chunk
                self.first = False
            else:
                self.tool_calls += chunk

            functions = self.tool_calls.message.additional_kwargs["tool_calls"]
            self.agent_message.tools = [
                {
                'id': i,
                'name': function["function"].get("name", ""),
                'args': function["function"].get("arguments", {}),
                'result': ""}
                for i, function in enumerate(functions)]
        else:
            self.agent_message.content = token
        if self.websocket:
            await self.websocket.send_json(self.agent_message.model_dump_json())


class LLMAgent:
    name: str
    llm: BaseChatModel
    system_prompt: str
    examples: List = []
    input_variables: List[str] = []
    message_template: str = ''
    tools: List = []

    def __init__(self, name: str, llm: BaseChatModel, system_prompt: str, **kwargs):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.examples = kwargs.get('examples', [])
        self.input_variables = kwargs.get('input_variables', [])
        self.message_template = kwargs.get('message_template', '')
        self.tools = kwargs.get('tools', [])

    def invoke(self, inputs: Dict[str, Any], response_format: Any = None):
        exec_time = time.time()
        prompt = self._build_prompt(
            system_prompt=self.system_prompt,
            examples=self.examples,
            input_variables=self.input_variables,
            message_template=self.message_template,
        )

        agent_message = AgentMessage(
            agent=self.name,
            content='',
            tools=[],
        )

        if response_format:
            chain = prompt | (
                self.llm.bind_tools(tools=self.tools) if len(self.tools) > 0 else self.llm).with_structured_output(
                response_format)
        else:
            chain = prompt | (self.llm.bind_tools(tools=self.tools) if len(self.tools) > 0 else self.llm)

        result = chain.invoke(inputs, config=inputs.get('config', {}))

        # Check if the response type matches the expected AIMessage
        if isinstance(result, AIMessage):
            agent_message.response_metadata = result.response_metadata.get("token_usage", {})
            agent_message.tools = result.tool_calls
            agent_message.content = result.content
        else:
            agent_message.content = result
        agent_message.execution_time = time.time() - exec_time

        logger.info(agent_message.content or agent_message.tools, extra={"agent_name": self.name})

        return agent_message

    async def ainvoke(self, inputs: Dict[str, Any], websocket: WebSocket = None) -> AgentMessage:
        exec_time = time.time()
        prompt = self._build_prompt(
            system_prompt=self.system_prompt,
            examples=self.examples,
            input_variables=self.input_variables,
            message_template=self.message_template,
        )

        agent_message = AgentMessage(
            agent=self.name,
            content='',
            tools=[],
        )

        config = inputs.get('config', {})
        config |= {'callbacks': [StreamCallbackHandler(agent_message, websocket)]}

        chain = prompt | (self.llm.bind_tools(tools=self.tools) if len(self.tools) > 0 else self.llm)

        result = AIMessageChunk(content="")
        async for chunk in chain.astream(inputs, config=config):
            result += chunk

        # Check if the response type matches the expected AIMessage
        if isinstance(result, AIMessage):
            agent_message.response_metadata = result.response_metadata.get("token_usage", {})
            agent_message.tools = result.tool_calls
            agent_message.content = result.content
        else:
            agent_message.content = result
        agent_message.execution_time = time.time() - exec_time

        logger.info(agent_message.content or agent_message.tools, extra={"agent_name": self.name})

        return agent_message

    @staticmethod
    def _build_prompt(
            system_prompt: str,
            examples: List[Dict[str, str]],
            input_variables: List[str],
            message_template: str
    ) -> ChatPromptTemplate:

        example_prompt = ChatPromptTemplate.from_messages(
            [
                HumanMessagePromptTemplate.from_template("{input}"),
                AIMessagePromptTemplate.from_template("{output}")
            ]
        )

        few_shot_prompt = FewShotChatMessagePromptTemplate(
            input_variables=input_variables,
            example_prompt=example_prompt,
            examples=examples
        )

        final_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                few_shot_prompt,
                MessagesPlaceholder(variable_name="history", optional=True),
                ("human", message_template),
            ]
        )

        return final_prompt
