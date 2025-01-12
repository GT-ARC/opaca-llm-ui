"""
Request and response models used in the FastAPI routes (and in some of the implementations).
"""
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from .utils import build_prompt


class Url(BaseModel):
    url: str
    user: str | None
    pwd: str | None


class Message(BaseModel):
    user_query: str
    api_key: str


class AgentMessage(BaseModel):
    """
    Stores individual information generated by the various agents
    """
    agent: str
    content: str = ''
    tools: List = []
    response_metadata: Dict[str, Any] = {}
    execution_time: float = .0


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


class OpacaLLMBackend(ABC):
    NAME: str
    llm: BaseChatModel

    @property
    @abstractmethod
    def default_config(self):
        pass

    @abstractmethod
    async def query(self, message: str, session: SessionData) -> Response:
        pass


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

    async def ainvoke(self, inputs: Dict[str, Any]) -> AgentMessage:
        exec_time = time.time()
        prompt = build_prompt(
            system_prompt=self.system_prompt,
            examples=self.examples,
            input_variables=self.input_variables,
            message_template=self.message_template,
        )

        chain = prompt | (self.llm.bind_tools(tools=self.tools) if len(self.tools) > 0 else self.llm)

        result = await chain.ainvoke(inputs, config=inputs.get('config', {}))

        # Checks if answer was generated by integrated model class or Llama proxy
        res_meta_data = {}
        tools = []
        if isinstance(result, AIMessage):
            res_meta_data = result.response_metadata.get("token_usage", {})
            tools = result.tool_calls
            result = result.content

        return AgentMessage(
            agent=self.name,
            content=result,
            tools=tools,
            response_metadata=res_meta_data,
            execution_time=time.time() - exec_time,
        )
