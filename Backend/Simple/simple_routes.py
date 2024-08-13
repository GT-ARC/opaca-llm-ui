from typing import Dict

import openai
import json
import requests

from ..opaca_proxy import proxy as opaca_proxy


system_prompt = """
You suggest web services to fulfil a given purpose.
You present the result as pseudo-code, including temporary variables if needed.
You know some agents providing different actions that you can use. Do not assume any other services.
If those services are not sufficient to solve the problem, just say so.
First, show only the pseudo code. Later, if the user says "do it", and only then, you repeat the first service call of the previous pseudo code in this specific JSON format and nothing else (not even Markup):
{
    "agentId": <AGENT-ID>,
    "action": <ACTION-NAME>,
    "params": {
        <NAME>: <VALUE>,
        ...
    }
}
Following is the list of available services described in JSON, which can be called as webservices:   
"""

class SimpleBackend:

    def __init__(self):
        self.messages = []
        self.config = {
            "llama-url": "http://10.0.64.101:11000",
            "llama-model": "llama3.1:70b",
            "gpt-model": "gpt-4o",
            "gpt-temp": None,
        }

    async def query(self, message: str, debug: bool, api_key: str) -> Dict:
        print("QUERY", message)
        self._update_system_prompt()
        self.messages.append({"role": "user", "content": message})

        response = self._query_internal(debug, api_key)
        self.messages.append({"role": "assistant", "content": response})

        print("RESPONSE:", repr(response))
        try:
            d = json.loads(response.strip("`json\n")) # strip markdown, if included
            print("Successfully parsed as JSON, calling service...")
            result = opaca_proxy.invoke_opaca_action(d["action"], d["agentId"], d["params"])
            response = f"Called `/invoke/{d['action']}/{d['agentId']}` with params `{d['params']}`.\n\nThe result of this step was: {repr(result)}"
            self.messages.append({"role": "system", "content": response})
        except Exception as e:
            print("Not JSON", type(e), e)

        return {"result": response, "debug": ""}
    
    async def history(self) -> list:
        return self.messages

    async def reset(self):
        self.messages = []
        self._update_system_prompt()

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = {k: conf.get(k, v) for k, v in self.config.items()}

    def _update_system_prompt(self):
        self.messages[:1] = [{"role": "system", "content": system_prompt + opaca_proxy.actions}]


class SimpleOpenAIBackend(SimpleBackend):

    def _query_internal(self, debug: bool, api_key: str) -> str:
        print("Calling GPT...")
        self.client = openai.OpenAI(api_key=api_key or None)  # use if provided, else from Env

        completion = self.client.chat.completions.create(model=self.config["gpt-model"], temperature=self.config["gpt-temp"], messages=self.messages)
        return completion.choices[0].message.content


class SimpleLlamaBackend(SimpleBackend):

    def _query_internal(self, debug: bool, api_key: str) -> str:
        print("Calling LLAMA...")
        result = requests.post(f'{self.config["llama-url"]}/api/chat', json={
            "messages": self.messages,
            "model": self.config["llama-model"],
            "stream": False,
            })
        return result.json()["message"]["content"]
