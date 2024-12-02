"""
Request and response models used in the FastAPI routes (and in some of the implementations).
"""

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
    """
    Stores individual information generated by the various agents
    """
    agent: str
    content: str = ''
    tools: List[str] = []
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
