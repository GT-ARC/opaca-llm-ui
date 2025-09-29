import logging
import time

from starlette.websockets import WebSocket

from ..abstract_method import AbstractMethod
from ..models import Response, AgentMessage, SessionData, ConfigParameter, ChatMessage, Chat
from ..utils import openapi_to_functions


SYSTEM_PROMPT = """You are a helpful ai assistant who answers user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. In this case, you will receive the results of tool calls of 
previous iterations. Evaluate, whether another tool call if necessary. 
If tools return nothing or simply complete without feedback 
you should still tell the user that. Once you have retrieved all necessary information, immediately generate a response 
to the user about the result and the retrieval process. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services. 
"""


logger = logging.getLogger(__name__)

class SimpleToolsMethod(AbstractMethod):
    NAME = "simple-tools"

    async def query_stream(self, message: str, session: SessionData, chat: Chat, websocket: WebSocket = None) -> Response:
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        response = Response(query=message)

        config = session.config.get(self.NAME, self.default_config())
        max_iters = config["max_rounds"]
        
        # Get tools and transform them into the OpenAI Function Schema
        try:
            tools, error = openapi_to_functions(await session.opaca_client.get_actions_openapi(inline_refs=True))
        except AttributeError as e:
            response.error = str(e)
            response.content = "ERROR: It seems you are not connected to a running OPACA platform!"
            return response
        if len(tools) > 128:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
            tools = tools[:128]

        # initialize message history
        messages = list(chat.messages)
        messages.append(ChatMessage(role="user", content=message))

        while response.iterations < max_iters:
            response.iterations += 1

            # call the LLM with function-calling enabled
            result = await self.call_llm(
                session=session,
                model=config["model"],
                agent="assistant",
                system_prompt=SYSTEM_PROMPT,
                messages=messages,
                temperature=config["temperature"],
                tools=tools,
                websocket=websocket,
            )
            response.agent_messages.append(result)

            try:
                if not result.tools:
                    break

                tool_entries = [
                    await self.invoke_tool(session, call["name"], call["args"], response.iterations)
                    for call in result.tools
                ]
                tool_contents = "\n".join(
                    f"The result of tool '{tool['name']}' with parameters '{tool['args']}' was: {tool['result']}"
                    for tool in tool_entries
                )
                messages.append(ChatMessage(
                    role="user",
                    content=f"A user had the following request: {message}\n"
                            f"You have used the following tools: \n{tool_contents}")
                )
                response.agent_messages[-1].tools = tool_entries
                
            except Exception as e:
                error = f"There was an error in simple_tools_routes: {e}"
                messages.append(ChatMessage(role="system", content=error))
                response.agent_messages.append(AgentMessage(agent="system", content=error))
                response.error += f"{e}\n"
        else:
            response.error += "Maximum number of iterations reached.\n"

        response.content = result.content
        response.execution_time = time.time() - exec_time
        return response

    @property
    def config_schema(self) -> dict:
        return {
            "model": self.make_llm_config_param(name="Model", description="The model to use."),
            "temperature": ConfigParameter(
                name="Temperature",
                description="Temperature for the models",
                type="number",
                required=True,
                default=0.0,
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
        }
