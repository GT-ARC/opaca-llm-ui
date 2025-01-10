"""
Request and response models used in the FastAPI routes (and in some of the implementations).
"""
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler, StdOutCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import GenerationChunk, ChatGenerationChunk
from pydantic import BaseModel
from starlette.websockets import WebSocket

from .utils import build_prompt


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
    websocket: Optional[WebSocket] = None

    @property
    @abstractmethod
    def default_config(self):
        pass

    @abstractmethod
    async def query(self, message: str, session: SessionData) -> Response:
        pass

    async def query_stream(self, message: str, session: SessionData, websocket: Optional[WebSocket] = None) -> Response:
        pass


class StreamCallbackHandler(BaseCallbackHandler):
    tool_calls = None
    first = True
    websocket: Optional[WebSocket] = None
    agent_message: AgentMessage

    def __init__(self, agent_message: AgentMessage, websocket: Optional[WebSocket] = None):
        self.agent_message = agent_message
        self.websocket = websocket

    async def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        if chunk.message.additional_kwargs.get('tool_calls', {}):
            if self.first:
                self.tool_calls = chunk
                self.first = False
            else:
                self.tool_calls += chunk
            self.agent_message.tools = self.tool_calls.message.additional_kwargs['tool_calls']
        else:
            self.agent_message.content = token
        await self.websocket.send_json(self.agent_message.model_dump_json())


class LLMAgent:
    name: str
    llm: BaseChatModel
    system_prompt: str
    examples: List = []
    input_variables: List[str] = []
    message_template: str = ''
    tools: List = []
    websocket: Optional[WebSocket] = None

    def __init__(self, name: str, llm: BaseChatModel, system_prompt: str, **kwargs):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.examples = kwargs.get('examples', [])
        self.input_variables = kwargs.get('input_variables', [])
        self.message_template = kwargs.get('message_template', '')
        self.tools = kwargs.get('tools', [])
        self.websocket = kwargs.get('websocket', None)

    async def ainvoke(self, inputs: Dict[str, Any]) -> AgentMessage:
        exec_time = time.time()
        prompt = build_prompt(
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
        config |= {'callbacks': [StreamCallbackHandler(agent_message, self.websocket)]}

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

        return agent_message
