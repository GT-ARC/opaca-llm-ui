import logging
import time

from starlette.websockets import WebSocket

from ..abstract_method import AbstractMethod
from ..models import Response, AgentMessage, SessionData, ConfigParameter, ChatMessage
from ..utils import openapi_to_functions


system_prompt = """You are a helpful ai assistant who answers user queries with the help of 
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

class SimpleToolsBackend(AbstractMethod):
    NAME = "simple-tools"

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)

    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        result = Response(query=message)

        config = session.config.get(self.NAME, self.default_config())
        
        # Get tools and transform them into the OpenAI Function Schema
        try:
            tools, error = openapi_to_functions(await session.opaca_client.get_actions_openapi(inline_refs=True), config['use_agent_names'])
        except AttributeError as e:
            result.error = str(e)
            result.content = "ERROR: It seems you are not connected to a running OPACA platform!"
            return result
        if len(tools) > 128:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
            tools = tools[:128]

        # initialize message history
        messages = session.messages.copy()
        messages.append(ChatMessage(role="user", content=message))
                   
        while result.iterations < 10:

            result.iterations += 1

            # call the LLM with function-calling enabled
            response = await self.call_llm(
                session=session,
                model=config["model"],
                agent="assistant",
                system_prompt=system_prompt,
                messages=messages,
                temperature=config["temperature"],
                tools=tools,
                websocket=websocket,
            )

            # record assistant message
            result.agent_messages.append(AgentMessage(
                agent="assistant",
                content=response.content,
                response_metadata=response.response_metadata,
                execution_time=response.execution_time,
            ))

            try:
                if not response.tools:
                    result.content = response.content
                    break

                tool_contents = ""
                tool_entries = []
                
                for call in response.tools:
                    if config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    params = call["args"].get("requestBody", {})
                
                    # invoke via OPACA client
                    try:
                        action_result = await session.opaca_client.invoke_opaca_action(
                            action_name, agent=agent_name, params=params
                        )
                    except Exception as e:
                        action_result = None
                        result.error += f"Failed to invoke action {action_name}. Cause: {e}"
                
                    # collect tool result details
                    tool_contents += f"The result of tool '{action_name}' with parameters '{params}' was: {action_result}\n"
                    tool_entries.append({
                        "id": result.iterations,
                        "name": call["name"],
                        "args": params,
                        "result": action_result
                    })
                
                # Append one unified message after loop
                if tool_contents:
                    messages.append(ChatMessage(role="user",
                                                content=f"A user had the following request: {message}\n"
                                                        f"You have used the following tools: \n{tool_contents}"))
                    result.agent_messages[-1].tools = tool_entries
                
            except Exception as e:
                error = f"There was an error in simple_tools_routes: {e}"
                messages.append(ChatMessage(role="system", content=error))
                result.agent_messages.append(AgentMessage(agent="system", content=error))
                result.error = str(e)

        result.execution_time = time.time() - exec_time
        return result

    @property
    def config_schema(self) -> dict:
        return {
            "model": self.make_llm_config_param(),
            "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
            "use_agent_names": ConfigParameter(type="boolean", required=False, default=True),
        }
