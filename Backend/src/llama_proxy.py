import requests

from typing import Any, Dict, Optional, List, Union, Sequence, Tuple
from langchain.chains.base import Chain
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import RunnableConfig


class OpacaLLM(BaseChatModel):
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

    def invoke(
            self,
            input: Union[PromptValue, str, Sequence[Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]]],
            config: Optional[RunnableConfig] = None,
            stop: Optional[List[str]] = None,
            **kwargs: Any
    ) -> Dict[str, Any]:
        return self._generate(input.to_messages(), stop, None, **config.get('metadata', {}))

    def _generate(
            self,
            messages,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any
    ) -> Dict[str, Any]:

        response = requests.post(
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
            }
        ).json()

        tool_calls = response['message'].get('tool_calls', [])

        response = response['message']['content']

        output = response.replace("\\n", "\n").replace('\\"', '"').strip()

        for word in stop:
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return {"result": output, "tool_calls": tool_calls}

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
