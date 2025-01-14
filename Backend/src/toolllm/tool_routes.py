import re
import time

from langchain_core.messages import HumanMessage, AIMessage

from .tool_method import ToolMethod
from ..models import Response, SessionData, OpacaLLMBackend


class ToolLLMBackend(OpacaLLMBackend):
    max_iter: int = 5

    def __init__(self, method: str):
        self.method = ToolMethod.create_method(method)

    @property
    def default_config(self):
        return self.method.config

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session, None)

    async def query_stream(self, message: str, session: SessionData, websocket=None) -> Response:

        # Initialize parameters
        tool_names = []
        tool_params = []
        tool_results = []
        tool_responses = []
        result = None
        c_it = 0
        should_continue = True

        # Initialize the response object
        response = Response()
        response.query = message

        # Set config
        config = session.config.get(self.method.name, self.default_config)

        # Save time before execution
        total_exec_time = time.time()

        try:
            await self.method.init_agents(session, config)
        except Exception as e:
            print(e)
            response.error = str(e)
            response.content = ("I am sorry, but I encountered a problem during initialization. This is the error that "
                                f"was given to me:\n\n\"{e}\"")
            return response

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:
            result = await self.method.invoke_generator(session, message, tool_responses, config, websocket=websocket)

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := self.method.check_valid_action(result.tools)) and correction_limit < 3:
                full_err += err_msg
                result = await self.method.invoke_generator(session, message, tool_responses, config, full_err,
                                                            websocket=websocket)
                correction_limit += 1

            response.agent_messages.append(result)

            # Check if tools were generated and if so, execute them by calling the opaca-proxy
            for i, call in enumerate(result.tools):

                tool_names.append(call['name'])
                tool_params.append(call['args'])
                try:
                    if config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    tool_results.append(
                        await session.client.invoke_opaca_action(
                            action_name,
                            agent_name,
                            call['args'].get('requestBody', {})
                        ))
                except Exception as e:
                    tool_results.append(str(e))

                # The format should match the one in the StreamCallbackHandler
                result.tools[i] = (f'Tool {len(tool_names)}: \n'
                                   f'\tName: {call["name"]},\n'
                                   f'\tArguments: {call["args"]},\n'
                                   f'\tResults: {tool_results[-1]}\n')

            # If a websocket was defined, send the tools WITH their results to the frontend
            if websocket:
                await websocket.send_json(result.model_dump_json())

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tools) > 0:
                result = await self.method.invoke_evaluator(
                    message,  # Original user query
                    tool_names,  # ALL the tools used so far
                    tool_params,  # ALL the parameters used for the tools
                    tool_results,  # ALL the results from the opaca action calls
                    websocket=websocket  # Websocket for llm token streaming
                )
                response.agent_messages.append(result)

                # Check if llm agent thinks user query has not been fulfilled yet
                should_continue = True if re.search(r"\bCONTINUE\b", result.content) else False

                # Remove the keywords from the generated response
                result.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result.content).strip()

                # Add generated response to internal history to give result to first llm agent
                tool_responses.append(AIMessage(result.content))
            else:
                should_continue = False

            c_it += 1

        # Add query and final response to global message history
        session.messages.append(HumanMessage(message))
        session.messages.append(AIMessage(result.content))

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        return response
