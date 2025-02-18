import logging
import time

import openai
import json
import httpx

from ..models import Response, AgentMessage, SessionData, OpacaLLMBackend, ConfigParameter
from ..utils import message_to_dict, message_to_class

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

logger = logging.getLogger("src.models")

class SimpleBackend(OpacaLLMBackend):

    def __init__(self):
        self.messages = []
        self.config = self.default_config()

    async def query(self, message: str, session: SessionData) -> Response:
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        result = Response(query=message)

        # initialize messages with system prompt and previous messages
        policy = ask_policies[int(session.config.get("ask_policy", self.config["ask_policy"]))]
        actions = session.client.actions if session.client else "(No services, not connected yet.)"
        self.messages = [
            {"role": "system", "content": system_prompt % (policy, actions)},
            *map(message_to_dict, session.messages)
        ]
        # new conversation starts here
        last_msg = len(self.messages)
        self.messages.append({"role": "user", "content": message})

        while True:
            result.iterations += 1
            response = await self._query_internal(session.api_key, session)
            self.messages.append({"role": "assistant", "content": response})
            result.agent_messages.append(AgentMessage(agent="assistant", content=response))

            logger.info(repr(response), extra={"agent_name": "assistant"})
            try:
                d = json.loads(response.strip("`json\n")) # strip markdown, if included
                if type(d) is not dict or any(x not in d for x in ("action", "agentId", "params")):
                    logger.info("JSON, but not an action call...")
                    break
                logger.info("Successfully parsed as JSON, calling service...")
                action_result = await session.client.invoke_opaca_action(d["action"], d["agentId"], d["params"])
                response = f"The result of this step was: {repr(action_result)}"
                self.messages.append({"role": "system", "content": response})
                result.agent_messages.append(AgentMessage(
                    agent="system",
                    content=response,
                    tools=[{"id": result.iterations,
                            "name": f'{d["agentId"]}--{d["action"]}',
                            "args": d["params"],
                            "result": action_result}]))
                logger.info(response, extra={"agent_name": "system"})
            except json.JSONDecodeError as e:
                logger.info(f"Not JSON: {type(e)}, {e}")
                break
            except Exception as e:
                logger.info(f"ERROR: {type(e)}, {e}")
                response = f"There was an error: {e}"
                self.messages.append({"role": "system", "content": response})
                result.agent_messages.append(AgentMessage(agent="system", content=response))
                logger.info(response, extra={"agent_name": "system"})
                result.error = str(e)
                break

        result.content = response
        session.messages.extend([message_to_class(msg) for msg in self.messages[last_msg:]])
        result.execution_time = time.time() - exec_time
        return result

    @property
    def config_schema(self) -> dict:
        return self._init_config()


class SimpleOpenAIBackend(SimpleBackend):

    NAME = "simple-openai"

    @staticmethod
    def _init_config():
        return {
            "model": ConfigParameter(type="string", required=True, default="gpt-4o-mini"),
            "temperature": ConfigParameter(type="number", required=True, default=1.0, minimum=0.0, maximum=2.0),
            "ask_policy": ConfigParameter(type="integer", required=True, default=0, enum=[*range(0, len(ask_policies))]),
        }

    async def _query_internal(self, api_key: str, session: SessionData) -> str:
        # Set config
        self.config = session.config.get(SimpleOpenAIBackend.NAME, self.default_config())
        self.client = openai.AsyncOpenAI(api_key=api_key or None)  # use if provided, else from Env

        completion = await self.client.chat.completions.create(
            model=self.config["model"],
            messages=self.messages,
            temperature=float(self.config["temperature"]),
        )
        return completion.choices[0].message.content


class SimpleLlamaBackend(SimpleBackend):

    NAME = "simple-llama"

    @staticmethod
    def _init_config():
        return {
            "api-url": ConfigParameter(type="string", required=True, default="http://10.0.64.101:11000"),
            "model": ConfigParameter(type="string", required=True, default="llama3.1:70b"),
            "temperature": ConfigParameter(type="number", required=True, default=1.0, minimum=0.0, maximum=2.0),
            "ask_policy": ConfigParameter(type="integer", required=True, default=0, enum=[*range(0, len(ask_policies))]),
        }

    async def _query_internal(self, api_key: str, session: SessionData) -> str:
        # Set config
        self.config = session.config.get(SimpleLlamaBackend.NAME, self.default_config())

        async with httpx.AsyncClient() as client:
            result = await client.post(f'{self.config["api-url"]}/api/chat', json={
                "model": self.config["model"],
                "messages": self.messages,
                "stream": False,
                "options": {
                    "temperature": float(self.config["temperature"]),
                    "num_ctx": 32768,  # consider last X tokens for response
                }
            })
        return result.json()["message"]["content"]
