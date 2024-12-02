from typing import Dict

import openai
import json
import requests
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..models import Response, AgentMessage, SessionData
from ..opaca_client import client as opaca_client
from ..utils import convert_message

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

The result of the action invocation is then fed back into the prompt as a system message.
If a follow-up action is needed to fulfill the user's request, output that action call in the same format until the user's request is fulfilled.
Once the user's request is fulfilled, respond normally, presenting the final result to the user and telling them (briefly) which actions you called to get there.

It is VERY important to follow this format, as we will try to parse it, and call the respective action if successful.
So print ONLY the above JSON, do NOT add a chatty message like "executing service ... now" or "the result of the last step was ..., now calling ..."!
Again, in order to call a service, your response must ONLY contain the JSON and nothing else.

%s

Following is the list of available agents and actions described in JSON:
%s
"""

ask_policies = [
    "Directly execute the action you find best fitting without asking the user for confirmation.",
    "Directly execute the action if the selection is clear and only contains a single action, otherwise present your plan to the user and ask for confirmation once.",
    "Before executing the action (or actions), always show the user what you are planning to do and ask for confirmation."
]

class SimpleBackend:

    def __init__(self):
        self.messages = []
        self.config = self._init_config()

    async def query(self, message: str, debug: bool, api_key: str, session: SessionData) -> Response:
        print("QUERY", message)
        self._update_system_prompt()
        self.messages.extend([convert_message(msg) for msg in session.messages])
        last_msg = len(self.messages)
        self.messages.append({"role": "user", "content": message})
        result = Response(query=message)

        while True:
            result.iterations += 1
            response = self._query_internal(debug, api_key, session)
            self.messages.append({"role": "assistant", "content": response})

            print("RESPONSE:", repr(response))
            try:
                d = json.loads(response.strip("`json\n")) # strip markdown, if included
                if type(d) is not dict or any(x not in d for x in ("action", "agentId", "params")):
                    print("JSON, but not an action call...")
                    break
                print("Successfully parsed as JSON, calling service...")
                action_result = opaca_client.invoke_opaca_action(d["action"], d["agentId"], d["params"])
                response = f"The result of this step was: {repr(action_result)}"
                self.messages.append({"role": "system", "content": response})
            except json.JSONDecodeError as e:
                print("Not JSON", type(e), e)
                break
            except Exception as e:
                print("ERROR", type(e), e)
                response = f"There was an error: {e}"
                self.messages.append({"role": "system", "content": response})
                result.error = str(e)
                break

        result.content = response
        result.agent_messages = [AgentMessage(agent=msg["role"], content=msg["content"]) for msg in self.messages[last_msg:]]
        session.messages.extend([convert_message(msg) for msg in self.messages[last_msg:]])
        return result

    async def get_config(self) -> dict:
        return self._init_config()

    def _update_system_prompt(self):
        policy = ask_policies[int(self.config["ask_policy"])]
        self.messages = [{"role": "system", "content": system_prompt % (policy, opaca_client.actions)}]


class SimpleOpenAIBackend(SimpleBackend):

    def _init_config(self):
        return {
            "model": "gpt-4o-mini",
            "temperature": 1.0,
            "ask_policy": 0,
        }

    def _query_internal(self, debug: bool, api_key: str, session: SessionData) -> str:
        print("Calling GPT...")
        # Set config
        self.config = session.config.get("simple-openai", self._init_config())
        self.client = openai.OpenAI(api_key=api_key or None)  # use if provided, else from Env

        completion = self.client.chat.completions.create(
            model=self.config["model"],
            messages=self.messages,
            temperature=float(self.config["temperature"]),
        )
        return completion.choices[0].message.content


class SimpleLlamaBackend(SimpleBackend):

    def _init_config(self):
        return {
            "api-url": "http://10.0.64.101:11000",
            "model": "llama3.1:70b",
            "temperature": 1.0,
            "ask_policy": 0,
        }

    def _query_internal(self, debug: bool, api_key: str, session: SessionData) -> str:
        print("Calling LLAMA...")
        # Set config
        self.config = session.config.get("simple-llama", self._init_config())
        result = requests.post(f'{self.config["api-url"]}/api/chat', json={
            "model": self.config["model"],
            "messages": self.messages,
            "stream": False,
            "options": {
                "temperature": float(self.config["temperature"]),
                "num_ctx": 32768,  # consider last X tokens for response
            }
        })
        return result.json()["message"]["content"]
