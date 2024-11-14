import requests

from typing import Any, Dict, Optional, List
from langchain.chains.base import Chain
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompt_values import PromptValue
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
        return ["messages"]

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
                'messages': self._format_llama3(inputs["messages"]),
                'model': self.model,
                'stream': False,
                'options': {
                    'temperature': 0.0,
                    'num_ctx': 32768
                }
            }
        ).json()

        print(f'Raw output: {response}')

        response = response['message']['content']

        output = response.replace("\\n", "\n").replace('\\"', '"').strip()

        for word in inputs.get('stop_words', []):
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return {"result": output}

    @staticmethod
    def _format_llama3(input_messages):
        messages = []

        for message in input_messages:
            if isinstance(message, SystemMessage):
                role = "system"
            elif isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                raise ValueError(f'Unknown message type: {type(message)}')

            content = message.content
            content = content.replace("\\n", "").replace('\\"', '"')

            messages.append({"role": role, "content": content})
        return messages
