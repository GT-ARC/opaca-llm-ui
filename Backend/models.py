from typing import List, Dict, Any

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

class Response(BaseModel):
    query: str = ''
    agent_messages: List[AgentMessage] = []
    iterations: int = 0
    execution_time: float = .0
    content: str = ''
    error: str = ''

class CustomResponse(JSONResponse):
    def __init__(
        self,
        model: Response,
        session_id: str = None,
        status_code: int = 200,
        **kwargs
    ):
        content = model.model_dump()
        super().__init__(content=content, status_code=status_code, **kwargs)

        if session_id:
            self.set_cookie(key='session_id', value=session_id, httponly=True)
