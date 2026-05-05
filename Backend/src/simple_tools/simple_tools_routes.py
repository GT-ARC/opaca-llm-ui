import logging
import time

from ..abstract_method import AbstractMethod
from ..models import QueryResponse, AgentMessage, ChatMessage, MethodConfig, LLMConfig, ResetTextMessage

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


class SimpleToolConfig(MethodConfig):
    model: LLMConfig = MethodConfig.llm_role(title='Simple Tools Agent', description='The model to use')
    max_rounds: int = MethodConfig.max_rounds_field()


class SimpleToolsMethod(AbstractMethod):
    NAME = "simple-tools"
    CONFIG = SimpleToolConfig

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def query(self) -> QueryResponse:
        exec_time = time.time()
        logger.info(self.response.query, extra={"agent_name": "user"})

        config: SimpleToolConfig = self.get_config()
        max_iters = config.max_rounds

        # Get tools and transform them into the OpenAI Function Schema
        tools, error = await self.get_tools()

        # initialize message history
        messages = list(self.chat.messages)
        messages.append(ChatMessage(role="user", content=self.response.query))

        while self.response.iterations < max_iters:
            await self.send_to_websocket(ResetTextMessage(chat_id=self.chat.chat_id))
            self.response.iterations += 1

            # call the LLM with function-calling enabled
            result = await self.call_llm(
                model_config=config.model,
                agent="assistant",
                system_prompt=self.build_full_prompt(SYSTEM_PROMPT),
                messages=messages,
                tools=tools,
                is_output=True,
            )
            self.response.agent_messages.append(result)

            try:
                if not result.tools:
                    break

                tool_entries = [
                    await self.invoke_tool(call.name, call.args, call.id)
                    for call in result.tools
                ]
                tool_contents = "\n".join(
                    f"The result of tool '{tool.name}' with parameters '{tool.args}' was: {tool.result}"
                    for tool in tool_entries
                )
                messages.append(ChatMessage(
                    role="user",
                    content=f"A user had the following request: {self.response.query}\n"
                            f"You have used the following tools: \n{tool_contents}")
                )
                self.response.agent_messages[-1].tools = tool_entries

            except Exception as e:
                error = f"There was an error in simple_tools_routes: {e}"
                messages.append(ChatMessage(role="system", content=error))
                self.response.agent_messages.append(AgentMessage(agent="system", content=error))
                self.response.error += f"{e}\n"
        else:
            self.response.error += "Maximum number of iterations reached.\n"

        self.response.content = result.content
        self.response.execution_time = time.time() - exec_time
        return self.response
