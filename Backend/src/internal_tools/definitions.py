from typing import Callable

from pydantic import BaseModel


INTERNAL_TOOLS_AGENT_NAME = "LLM-Assistant"


class InternalTool(BaseModel):
    name: str
    description: str
    params: dict[str, str]
    required_params: list[str] | None = None
    result: str
    function: Callable
    requires_code_execution: bool = False
