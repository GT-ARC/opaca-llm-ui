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
                    {"role": "system", "content": "If you use tools, answer only in the following format, even if no parameters are necessary for a tool:\n\n"
                                                  "{\"name\": \"ToolName\", \"parameters\": {\"ParameterName\", Value}}\n\n"
                                                  "If you generate multiple tool calls, separate them with semicolons.\n"
                                                  "All of the keys and the tool name need to be surrounded by quotation marks.\n\n"
                                                  "If you do not generate a tool call, start your Answer by outputting the word \"STOP\"."
                                                  "If the user asks you about your functionality or how you can assist them, output a summary of the tools you can provide based on the list of actions given in that message."
                                                  "If a user asks about a specific tool or service, provide them with the asked information."
                                                  "Parameter values should only be surrounded by quotation marks if they are meant to be string values."},
                    {"role": "user", "content": inputs.get('input', '').to_string()}
                ],
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
