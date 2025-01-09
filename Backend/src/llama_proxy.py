import httpx

from typing import Any, Dict, Optional, List, Union, Sequence, Tuple
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolCall
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig


class LlamaProxy(BaseChatModel):
    url: str = ""
    model: str = ""
    tools: List = []

    def __init__(self, url: str, model: str) -> None:
        super().__init__()
        self.url = url
        self.model = model

    @property
    def _llm_type(self) -> str:
        return "Llama-3 Proxy"

    def bind_tools(self, tools: List):
        self.tools = tools
        return self

    async def ainvoke(
            self,
            input: Union[PromptValue, str, Sequence[Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]]],
            config: Optional[RunnableConfig] = None,
            stop: Optional[List[str]] = None,
            **kwargs: Any
    ) -> AIMessage:
        return await self._generate(input.to_messages(), stop, None, **config.get('metadata', {}))

    async def _generate(
            self,
            messages,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any
    ) -> AIMessage:

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{self.url}/api/chat',
                json={
                    'messages': self._format_llama3(messages),
                    'model': self.model,
                    'stream': False,
                    'tools': self.tools,
                    'options': {
                        'temperature': kwargs.get("temperature", 0),
                        'num_ctx': kwargs.get("num_ctx", 32768)
                    }
                },
                timeout=None    # This could lead to some loops, but necessary for possible demos etc.
            )
            response = response.json()

        tool_calls = [ToolCall(name=call["function"]["name"], args=call["function"]["arguments"], id="")
                      for call in response['message'].get('tool_calls', [])]

        response = response['message']['content']

        content = response.replace("\\n", "\n").replace('\\"', '"').strip()

        for word in stop or []:
            stop_pos = content.find(word)
            if stop_pos != -1:
                return content[:stop_pos].strip()

        return AIMessage(content=content, tool_calls=tool_calls, response_meta_data={})

    @staticmethod
    def _format_llama3(messages):
        messages_out = []
        system_message = []

        # Transform all message objects into llama messages
        for message in messages:
            if isinstance(message, SystemMessage):
                system_message = [{"role": "system", "content": message.content}]
                continue
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                raise ValueError(f'Unknown message type: {type(message)}')

            messages_out.append({"role": role, "content": message.content})

        return system_message + messages_out
