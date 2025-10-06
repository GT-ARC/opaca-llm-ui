from typing import List, Optional, Dict, Any

from mistralai import Mistral, UserMessage, SystemMessage, AssistantMessage

from .BaseLLMClient import BaseLLMClient


class MistralClient(BaseLLMClient):

    def __init__(self, api_key: str, base_url: str = None):
        super().__init__(api_key, base_url)
        self.client = Mistral(api_key=api_key)

    async def query(
            self,
            messages: List,
            model: str,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            **kwargs
    ) -> str:
        pass

    async def stream(
            self,
            messages: List,
            model: str,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            **kwargs
    ) -> str:

        new_msgs = []
        for message in messages:
            if message.role == "user":
                new_msgs.append(UserMessage(content=message.content))
            elif message.role == "system":
                new_msgs.append(SystemMessage(content=message.content))
            elif message.role == "assistant":
                new_msgs.append(AssistantMessage(content=message.content))

        response = await self.client.chat.stream_async(
            model=model,
            messages=new_msgs,
            tools=tools,
            tool_choice=tool_choice,
        )

        result = ""

        async for chunk in response:
            if chunk.data.choices[0].delta.content is not None:
                print(chunk.data.choices[0].delta.content, end="", flush=True)
                result += chunk.data.choices[0].delta.content

        return result
