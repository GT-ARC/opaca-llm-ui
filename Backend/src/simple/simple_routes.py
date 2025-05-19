import logging
import time

import json

from starlette.websockets import WebSocket

from ..abstract_method import AbstractMethod
from ..models import Response, AgentMessage, SessionData, ConfigParameter, ChatMessage

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

ask_policies = {
    "never": "Directly execute the action you find best fitting without asking the user for confirmation.",
    "relaxed": "Directly execute the action if the selection is clear and only contains a single action, otherwise present your plan to the user and ask for confirmation once.",
    "always": "Before executing the action (or actions), always show the user what you are planning to do and ask for confirmation.",
}

#logger = logging.getLogger("src.models")
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()
class SimpleBackend(AbstractMethod):

    NAME = "simple"

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)

    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        result = Response(query=message)

        config = session.config.get(self.NAME, self.default_config())

        # initialize messages
        policy = ask_policies[config["ask_policy"]]
        actions = session.client.actions if session.client else "(No services, not connected yet.)"
        messages = session.messages.copy()

        # new conversation starts here
        messages.append(ChatMessage(role="user", content=message))

        while True:
            logger.error("test")
            logger.info("test2")
            logging.error("test")
            logging.info("test2")
            result.iterations += 1
            response = await self.call_llm(
                model=config["model"],
                agent="assistant",
                system_prompt=system_prompt % (policy, actions),
                messages=messages,
                temperature=config["temperature"],
                tool_choice="none",
                websocket=websocket,
            )
            messages.append(ChatMessage(role="assistant", content=response.content))
            result.agent_messages.append(AgentMessage(
                agent="assistant",
                content=response.content,
                response_metadata=response.response_metadata,
                execution_time=response.execution_time,
            ))

            try:
                d = json.loads(response.content.strip("`json\n")) # strip markdown, if included
                if type(d) is not dict or any(x not in d for x in ("action", "agentId", "params")):
                    logger.info("JSON, but not an action call...")
                    break
                logger.info("Successfully parsed as JSON, calling service...")
                action_result = await session.client.invoke_opaca_action(d["action"], d["agentId"], d["params"])
                tool_result_response = f"The result of this step was: {repr(action_result)}"
                messages.append(ChatMessage(role="assistant", content=tool_result_response))
                result.agent_messages.append(AgentMessage(
                    agent="assistant",
                    content=tool_result_response,
                    tools=[{"id": result.iterations,
                            "name": f'{d["agentId"]}--{d["action"]}',
                            "args": d["params"],
                            "result": action_result}])
                )
                logger.info(response, extra={"agent_name": "system"})

                # Stream tool results
                if websocket:
                    await websocket.send_json(result.agent_messages[-1].model_dump_json())
            except json.JSONDecodeError as e:
                logger.info(f"Not JSON: {type(e)}, {e}")
                break
            except Exception as e:
                logger.info(f"ERROR: {type(e)}, {e}")
                error = f"There was an error: {e}"
                messages.append(ChatMessage(role="system", content=error))
                result.agent_messages.append(AgentMessage(agent="system", content=error))
                logger.info(error, extra={"agent_name": "system"})
                result.error = str(e)
                break

        result.content = response.content
        result.execution_time = time.time() - exec_time
        return result

    @property
    def config_schema(self) -> dict:
        return {
            "model": ConfigParameter(type="string", required=True, default="gpt-4o-mini"),
            "temperature": ConfigParameter(type="number", required=True, default=1.0, minimum=0.0, maximum=2.0),
            "ask_policy": ConfigParameter(type="string", required=True, default="never",
                                          enum=list(ask_policies.keys())),
        }
