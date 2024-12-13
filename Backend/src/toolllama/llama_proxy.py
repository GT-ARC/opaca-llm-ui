import requests

from typing import Any, Dict, Optional, List
from langchain.chains.base import Chain
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig


class OpacaLLM(Chain):
    url: str = ""
    model: str = ""

    def __init__(self, url: str, model: str) -> None:
        super().__init__()
        self.url = url
        self.model = model

    @property
    def _llm_type(self) -> str:
        return "Llama-3 Proxy"

    @property
    def input_keys(self) -> List[str]:
        return ["messages", "history", "config", "tools"]

    @property
    def output_keys(self) -> List[str]:
        return ["result"]

    def _call(
            self,
            inputs: Dict[str, Any],
            config: Optional[RunnableConfig] = None,
            **kwargs: Any
    ) -> Dict[str, Any]:

        response = requests.post(
            f'{self.url}/api/chat',
            json={
                'messages': self._format_llama3(inputs["messages"], inputs["history"]),
                'model': self.model,
                'stream': False,
                'tools': inputs["tools"],
                'options': {
                    'temperature': inputs["config"].get("temperature", 0),
                    'num_ctx': inputs["config"].get("num_ctx", 32768)
                }
            }
        ).json()

        tool_calls = response['message'].get('tool_calls', [])

        response = response['message']['content']

        output = response.replace("\\n", "\n").replace('\\"', '"').strip()

        for word in inputs.get('stop_words', []):
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return {"result": output, "tool_calls": tool_calls}

    @staticmethod
    def _format_llama3(input_messages, message_history):
        messages = []
        system_message = []

        # Transform all message objects into llama messages
        for message in message_history + input_messages:
            if isinstance(message, SystemMessage):
                system_message = [{"role": "system", "content": message.content}]
                continue
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                raise ValueError(f'Unknown message type: {type(message)}')

            messages.append({"role": role, "content": message.content})

        return system_message + messages
