import openai
import requests
import json

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
class OpenAIBackend:

    def __init__(self, opaca_proxy):
        self.opaca_proxy = opaca_proxy
        self.client = openai.OpenAI()
        self.messages = []

    async def query(self, message: str) -> str:
        print("QUERY", message)
        self._update_system_prompt()
        self.messages.append({"role": "user", "content": message})
        completion = self.client.chat.completions.create(model="gpt-3.5-turbo", messages=self.messages)
        response = completion.choices[0].message.content
        print("RESPONSE:", repr(response))
        try:
            d = json.loads(response)
            result = await self.opaca_proxy.invoke_opaca_action(d["action"], d["agentId"], d["params"])
            response = f"Original response: `{response}`\n\nCalled `/invoke/{d['action']}/{d['agentId']}` with params `{d['params']}`.\n\nThe result of this step was: {repr(result)}"
        except Exception as e:
            print("NOT JSON", type(e), e)
        self.messages.append({"role": "assistant", "content": response})
        return response

    async def history(self):
        return self.messages

    async def reset(self):
        self.messages = []
        self._update_system_prompt()

    def _update_system_prompt(self):
        self.messages[:1] = [{"role": "system", "content": system_prompt + self.opaca_proxy.actions}]
        