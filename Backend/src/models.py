from typing import List, Dict, Any

from pydantic import BaseModel


class Url(BaseModel):
    url: str
    user: str | None
    pwd: str | None


class Message(BaseModel):
    user_query: str
    debug: bool
    api_key: str


class AgentMessage(BaseModel):
    agent: str
    content: str = ''
    tools: List[str] = []
    response_metadata: Dict[str, Any] = {}
    execution_time: float = .0

class Response(BaseModel):
    query: str = ''
    agent_messages: List[AgentMessage] = []
    iterations: int = 0
    execution_time: float = .0
    content: str = ''
    error: str = ''
