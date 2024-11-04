import requests

from typing import Any, Dict, Optional, List
from langchain.chains.base import Chain
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
        return ["input"]

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
                'messages': [
                    {"role": "user", "content": inputs.get('input', '').to_string()}
                ],
                'temperature': 0,
                'model': self.model,
                'stream': False,
            }
        ).json()['message']['content']

        output = response.replace("\\n", "\n").replace('\\"', '"').strip()

        for word in inputs.get('stop_words', []):
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return {"result": output}
