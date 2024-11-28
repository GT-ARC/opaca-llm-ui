"""
Request and response models used in the FastAPI routes (and in some of the implementations).
"""

from typing import List, Dict, Any, Optional

from docutils.nodes import status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.responses import JSONResponse


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


class ResponseData(BaseModel):
    query: str = ''
    agent_messages: List[AgentMessage] = []
    iterations: int = 0
    execution_time: float = .0
    content: str = ''
    error: str = ''


class Response(JSONResponse):
    def __init__(
            self,
            model: Optional[ResponseData] = None,
            session_id: str = None,
            status_code: int = 200,
            **kwargs
    ):
        content = jsonable_encoder(model) if model else {}
        super().__init__(content=content, status_code=status_code, **kwargs)

        if session_id:
            self.set_cookie('session_id', session_id, httponly=True)
