import logging
import time

import json

from starlette.websockets import WebSocket

from ..abstract_method import AbstractMethod
from ..models import QueryResponse, AgentMessage, SessionData, ConfigParameter, ChatMessage, Chat, ToolCall

SYSTEM_PROMPT = """
You are an assistant, called the 'OPACA-LLM'.

You have access to some 'agents', providing different 'actions' to fulfill a given purpose.
You are given the list of actions at the end of this prompt.
Do not assume any other services.
If those services are not sufficient to solve the problem, just say so.

In order to invoke an action with parameters, output the following JSON format and NOTHING else:
{{
    "agentId": <AGENT-ID>,
    "action": <ACTION-NAME>,
    "params": {{
        <NAME>: <VALUE>,
        ...
    }}
}}

The result of the action invocation is then fed back into the prompt as a system message.
If a follow-up action is needed to fulfill the user's request, output that action call in the same format until the user's request is fulfilled.
Once the user's request is fulfilled, respond normally, presenting the final result to the user and telling them (briefly) which actions you called to get there.

It is VERY important to follow this format, as we will try to parse it, and call the respective action if successful.
So print ONLY the above JSON, do NOT add a chatty message like "executing service ... now" or "the result of the last step was ..., now calling ..."!
Again, in order to call a service, your response must ONLY contain the JSON and nothing else.

{policy}

Following is the list of available agents and actions described in JSON:
{actions}
"""

ask_policies = {
    "never": "Directly execute the action you find best fitting without asking the user for confirmation.",
    "relaxed": "Directly execute the action if the selection is clear and only contains a single action, otherwise present your plan to the user and ask for confirmation once.",
    "always": "Before executing the action (or actions), always show the user what you are planning to do and ask for confirmation.",
}

logger = logging.getLogger(__name__)

class SimpleMethod(AbstractMethod):
    NAME = "simple"

    def __init__(self, session, websocket=None):
        super().__init__(session, websocket)

    async def query_stream(self, message: str, chat: Chat, websocket: WebSocket = None) -> QueryResponse:
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        response = QueryResponse(query=message)

        # Get session config
        config = self.session.config.get(self.NAME, self.default_config())
        max_iters = config["max_rounds"]

        prompt = SYSTEM_PROMPT.format(
            policy=ask_policies[config["ask_policy"]],
            actions=await self.get_actions(),
        )
        
        while response.iterations < max_iters:
            response.iterations += 1
            
            result = await self.call_llm(
                model=config["model"],
                agent="assistant",
                system_prompt=prompt,
                messages=[
                    *chat.messages,
                    ChatMessage(role="user", content=message),
                    *(ChatMessage(role=am.agent, content=am.content) for am in response.agent_messages),
                ],
                temperature=config["temperature"],
                tool_choice="none",
            )
            response.agent_messages.append(result)

            try:
                if not (tool := await self.find_tool(result.content)):
                    break

                tool_call = await self.invoke_tool(tool.name, tool.args, response.iterations-1)
                response.agent_messages.append(AgentMessage(
                    agent="assistant",
                    content=f"\nThe result of this step was: {tool_call.result}",
                    tools=[tool_call], # so that tool calls are properly shown in UI
                ))
                if websocket:
                    await websocket.send_json(response.agent_messages[-1].model_dump_json())
                
            except Exception as e:
                logger.info(f"ERROR: {type(e)}, {e}")
                response.agent_messages.append(AgentMessage(agent="assistant", content=f"There was an error: {e}"))
                response.error += f"{e}\n"
        else:
            response.error += "Maximum number of iterations reached.\n"

        response.content = result.content
        response.execution_time = time.time() - exec_time
        return response

    @classmethod
    def config_schema(cls) -> dict:
        return {
            "model": cls.make_llm_config_param(name="Model", description="The model to use."),
            "temperature": ConfigParameter(
                name="Temperature",
                description="Temperature for the models",
                type="number",
                required=True,
                default=1.0,
                minimum=0.0,
                maximum=2.0,
                step=0.1,
            ),
            "max_rounds": ConfigParameter(
                name="Max Rounds",
                description="Maximum number of retries",
                type="integer",
                required=True,
                default=5,
                minimum=1,
                maximum=10,
                step=1,
            ),
            "ask_policy": ConfigParameter(
                name="Ask Policy",
                description="Determine how much confirmation the LLM will require",
                type="string",
                required=True,
                default="never",
                enum=list(ask_policies.keys()),
            ),
        }

    async def get_actions(self):
        try:
            return await self.session._opaca_client.get_actions_simple()
        except:
            return "(No services, not connected yet.)"

    async def find_tool(self, llm_response: str) -> ToolCall | None:
        try:
            d = json.loads(llm_response.strip("`json\n")) # strip markdown, if included
            if type(d) is dict:
                return ToolCall(id=0, name=f'{d["agentId"]}--{d["action"]}', args=d["params"])
        except (json.JSONDecodeError, KeyError):
            pass
        return None
