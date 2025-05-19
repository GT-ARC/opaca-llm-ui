import logging
import time

from starlette.websockets import WebSocket

from ..abstract_method import AbstractMethod
from ..models import Response, AgentMessage, SessionData, ConfigParameter, ChatMessage
from ..utils import openapi_to_functions


system_prompt = """You are a helpful ai assistant that plans solution to user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. In those cases you should inform the user a new call
needs to be made with the intermediate results. If tools return nothing or simply complete without feedback 
you should still tell the user that. In general, you should always generate a response. If you can't, 
please put ut why. If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services.

%s

"""

ask_policies = {
    "never": "Directly execute the action you find best fitting without asking the user for confirmation.",
    "relaxed": "Directly execute the action if the selection is clear and only contains a single action, otherwise present your plan to the user and ask for confirmation once.",
    "always": "Before executing the action (or actions), always show the user what you are planning to do and ask for confirmation.",
}


logger = logging.getLogger("src.models")
logger.setLevel(logging.INFO)
class SimpleToolsBackend(AbstractMethod):
    NAME = "simple-tools"

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)

    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        exec_time = time.time()
        logger.error(message, extra={"agent_name": "user"})
        result = Response(query=message)

        config = session.config.get(self.NAME, self.default_config())

        # choose ask policy
        policy = ask_policies[config["ask_policy"]]
        
	# Get tools and transform them into the OpenAI Function Schema
        try:
            tools, error = openapi_to_functions(await session.client.get_actions_with_refs(), config['use_agent_names'])
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
        
        logging.info("simple tools is running")
        logger.info("simple tools is running")
                   
        while result.iterations < 10:
            logger.error("test")
            logger.info("test2")
            result.error = "test3"
            #print("test4")
            result.iterations += 1

            # call the LLM with function-calling enabled
            response = await self.call_llm(
                model=config["model"],
                agent="assistant",
                system_prompt=system_prompt % (policy), #, actions),
                messages=messages,
                temperature=config["temperature"],
                tools=tools,
                websocket=websocket,
            )

            # record assistant message
            messages.append(ChatMessage(role="assistant", content=response.content))
            result.agent_messages.append(AgentMessage(
                agent="assistant",
                content=response.content,
                response_metadata=response.response_metadata,
                execution_time=response.execution_time,
            ))

            try:
                # if the model returned any function calls, invoke them
                if getattr(response, "tools", None):
                    for call in response.tools:
                        action_name = call["name"]
                        params = call["args"].get("requestBody", {})
    
                        # invoke via OPACA client                       
                        action_result = await session.client.invoke_opaca_action(
                            action_name, agent = None, params=params
                        )
    
                        # append the tool result into the conversation
                        tool_result_response = f"The result of this step was: {repr(action_result)}"
                        messages.append(ChatMessage(role="assistant", content=tool_result_response))
                        """result.agent_messages.append(AgentMessage(
                            agent="assistant",
                            content=tool_result_response,
                            tools=[{
                                "id": result.iterations,
                                "name": call["name"],
                                "args": params,
                                "result": action_result
                            }]
                        ))"""

                else:

                    if response and response.content:
                        result.content = response.content
                        if not result.agent_messages:
                            result.agent_messages.append(AgentMessage(
                                agent="assistant",
                                content="no tool was used",
                                tools=[]
                            ))
                        logger.info("Dummy Agent message was added, without tools")


                    else:
                        logger.warning("Model response was empty (no content and no tools).")
                    break
                
            except Exception as e:
                print(f"ERROR: {type(e)}, {e}")
                error = f"There was an error in simple_tools_routes: {e}"
                messages.append(ChatMessage(role="system", content=error))
                result.agent_messages.append(AgentMessage(agent="system", content=error))
                result.error = str(e)

        result.content = response.content
        result.execution_time = time.time() - exec_time
        return result

    @property
    def config_schema(self) -> dict:
        return {
            "model": ConfigParameter(type="string", required=True, default="gpt-4o-mini"),
            "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
            "ask_policy": ConfigParameter(type="string", required=True, default="never",
                                          enum=list(ask_policies.keys())),
            "use_agent_names": ConfigParameter(type="boolean", required=False, default=False),

        }
