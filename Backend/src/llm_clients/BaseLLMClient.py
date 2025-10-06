from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseLLMClient(ABC):

    def __init__(self, key: str, base_url: str = None):
        self.key = key
        self.base_url = base_url

    @abstractmethod
    async def query(
            self,
            messages: List,
            model: str,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def stream(
            self,
            messages: List,
            model: str,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            **kwargs
    ) -> str:
        pass
