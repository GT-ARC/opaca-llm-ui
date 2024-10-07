from typing import Dict

import openai
import json
import requests

from ..RestGPT import Response, AgentMessage
from ..opaca_proxy import proxy as opaca_proxy


system_prompt = """
You are an assistant, called the 'OPACA-LLM'.

You have access to some 'agents', providing different 'actions' to fulfill a given purpose.
You are given the list of actions at the end of this prompt.
Do not assume any other services.
If those services are not sufficient to solve the problem, just say so.

In order to invoke an action with parameters, output the following JSON format and NOTHING else:
{
    "agentId": <AGENT-ID>,
    "action": <ACTION-NAME>,
    "params": {
        <NAME>: <VALUE>,
        ...
    }
}

It is VERY important to follow this format, as we will try to parse it, and call the respective action if successful.
So print ONLY the above JSON, do NOT add a chatty message like "executing service ... now" or "the result of the last step was ..."!
Again, in order to call a service, your response must ONLY contain the JSON and nothing else.

The result of the action invocation is then fed back into the prompt as a system message.
If a follow-up action is needed to fulfill the user's request, output that action call in the same format until the user's request is fulfilled.
Once the user's request is fulfilled, respond normally, presenting the final result to the user and telling them (briefly) which actions you called to get there.

If multiple actions will be needed to fulfill the request, first show which actions you are about to call (as a list), and only start calling the services (using the above format) once the user confirmed the plan with "okay", "do it", or similar. But if just a single action is needed, then you execute it directly without asking for confirmation first.

Again, please follow this exact process:
- if multiple actions have to be called:
  1. show a list of the actions to be called and ask the user to confirm this.
  2. wait for the user's input
  3. print the JSON for invoking the first action, and nothing else
  4. evaluate the result of the action (given as a system message)
  5. either respond to the user's original question, giving them the result, or continue with the next action (going back to 3.)
- if a only single action has to be called:
  1. print the JSON for invoking the action, and nothing else
  2. evaluate the result of the action (given as a system message)
  3. respond to the user's original question, giving them the result

Following is the list of available agents and actions described in JSON:
"""

class SimpleBackend:

    def __init__(self):
        self.messages = []
        self.config = self._init_config()

    async def query(self, message: str, debug: bool, api_key: str) -> Dict:
        print("QUERY", message)
        self._update_system_prompt()
        last_msg = len(self.messages)
        self.messages.append({"role": "user", "content": message})
        response_out = Response(query=message)

        while True:
            response = self._query_internal(debug, api_key)
            self.messages.append({"role": "assistant", "content": response})

            print("RESPONSE:", repr(response))
            try:
                d = json.loads(response.strip("`json\n")) # strip markdown, if included
                print("Successfully parsed as JSON, calling service...")
                result = opaca_proxy.invoke_opaca_action(d["action"], d["agentId"], d["params"])
                response = f"The result of this step was: {repr(result)}"
                self.messages.append({"role": "system", "content": response})
            except json.JSONDecodeError as e:
                print("Not JSON", type(e), e)
                break
            except Exception as e:
                print("ERROR", type(e), e)
                response = f"There was an error: {e}"
                self.messages.append({"role": "system", "content": response})
                break

        response_out.agent_messages.extend(AgentMessage(
            agent=msg["role"],
            content=msg["content"]
        ) for msg in self.messages[last_msg:])
        response_out.content = response
        return {"result": response_out}
    
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

    def _init_config(self):
        return {
            "model": "gpt-4o-mini",
            "temperature": None,
        }

    def _query_internal(self, debug: bool, api_key: str) -> str:
        print("Calling GPT...")
        self.client = openai.OpenAI(api_key=api_key or None)  # use if provided, else from Env

        completion = self.client.chat.completions.create(model=self.config["model"], temperature=self.config["temperature"], messages=self.messages)
        return completion.choices[0].message.content


class SimpleLlamaBackend(SimpleBackend):

    def _init_config(self):
        return {
            "api-url": "http://10.0.64.101:11000",
            "model": "llama3.1:70b",
        }

    def _query_internal(self, debug: bool, api_key: str) -> str:
        print("Calling LLAMA...")
        result = requests.post(f'{self.config["api-url"]}/api/chat', json={
            "messages": self.messages,
            "model": self.config["model"],
            "stream": False,
            })
        return result.json()["message"]["content"]
