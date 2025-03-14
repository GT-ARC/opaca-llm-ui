import re
import time
from typing import List

from .prompts import GENERATOR_PROMPT, EVALUATOR_TEMPLATE
from ..abstract_method import AbstractMethod
from ..models import Response, SessionData, ChatMessage, ConfigParameter
from ..utils import call_llm, openapi_to_functions


class ToolLLMBackend(AbstractMethod):
    max_iter: int = 5
    NAME = 'tool-llm'

    @property
    def config_schema(self):
        return {
                "model": ConfigParameter(type="string", required=True, default='gpt-4o-mini'),
                "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
                "use_agent_names": ConfigParameter(type="boolean", required=True, default=True),
               }

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)

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

        # Use config set in session, if nothing was set yet, use default values
        config = session.config.get(self.NAME, self.default_config())

        # Get tools and transform them into the OpenAI Function Schema
        tools, error = openapi_to_functions(await session.client.get_actions_with_refs(), config['use_agent_names'])
        if len(tools) > 128:
            tools = tools[:128]
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")

        # Save time before execution
        total_exec_time = time.time()

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:
            result = await call_llm(
                model=config['model'],
                agent='Tool Generator',
                system_prompt=GENERATOR_PROMPT,
                messages=session.messages + [{"role": "user", "content": message}] + tool_responses,
                temperature=config['temperature'],
                tools=tools,
                websocket=websocket,
            )

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := self.check_valid_action(tools, result.tools)) and correction_limit < 3:
                full_err += err_msg
                result = await call_llm(
                    model=config['model'],
                    agent='Tool Generator',
                    system_prompt=GENERATOR_PROMPT,
                    messages=session.messages + [{"role": "user", "content": message}] + tool_responses + [{"role": "user", "content": full_err}],
                    temperature=config['temperature'],
                    tools=tools,
                    websocket=websocket,
                )
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
                result.tools[i] = {
                    'id': len(tool_names),
                    'name': call['name'],
                    'args': call['args'],
                    'result': tool_results[-1]
                }

            # If a websocket was defined, send the tools WITH their results to the frontend
            if websocket:
                await websocket.send_json(result.model_dump_json())

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tools) > 0:
                result = await call_llm(
                    model=config['model'],
                    agent='Tool Evaluator',
                    system_prompt='',
                    messages=[ChatMessage(role="user", content=EVALUATOR_TEMPLATE.format(
                        message=message,
                        tool_names=tool_names,
                        tool_params=tool_params,
                        tool_results=tool_results,
                    ))],
                    temperature=config['temperature'],
                    tools=tools,
                    tool_choice="none",
                    websocket=websocket,
                )
                response.agent_messages.append(result)

                # Check if llm agent thinks user query has not been fulfilled yet
                should_continue = True if re.search(r"\bCONTINUE\b", result.content) else False

                # Remove the keywords from the generated response
                result.content = re.sub(r'\b(CONTINUE|FINISHED)\b', '', result.content).strip()

                # Add generated response to internal history to give result to first llm agent
                tool_responses.append(ChatMessage(role="assistant", content=result.content))
            else:
                should_continue = False

            c_it += 1

        # Add query and final response to global message history
        session.messages.append(ChatMessage(role="user", content=message))
        session.messages.append(ChatMessage(role="assistant", content=result.content))

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        response.error = error
        return response

    @staticmethod
    def check_valid_action(tools, calls: List[dict]) -> str:
        # Save all encountered errors in a single string, which will be given to the llm as an input
        err_out = ""

        # Since the gpt models can generate multiple tools, iterate over each generated call
        for call in calls:

            # Get the generated name and parameters
            action = call.get('name', '')
            args = call.get('args', {}).get('requestBody', {})

            # Check if the generated action name is found in the list of action definitions
            # If not, abort current iteration since no reference parameters can be found
            action_def = None
            for a in tools:
                if a['function']['name'] == action:
                    action_def = a['function']
            if not action_def:
                err_out += (f'Your generated function name "{action}" does not exist. Only use the exact function name '
                            f'defined in your tool section. Please make sure to separate the agent name and function '
                            f'name with two hyphens "--" if it is defined that way.\n')
                continue

            # Get the request body definition of the found action
            req_body = action_def['parameters']['properties'].get('requestBody', {})

            # Check if the generated parameters are in the right place (in the requestBody field) if the generated
            # action requires at least one parameter
            # If not, abort current iteration since we have to assume no parameters were generated at all
            if req_body.get('required', []) and not args:
                err_out += (f'For the function "{action}" you have not included any parameters in the request body, '
                            f'even though the function requires certain parameters. Please make sure to always put '
                            f'your generated parameters in the request body field.\n')
                continue

            # Check if all required parameters are present
            if missing := [p for p in req_body.get('required', []) if p not in args.keys()]:
                err_out += f'For the function "{action}" you have not included the required parameters {missing}.\n'

            # Check if no parameter is hallucinated
            if hall := [p for p in args.keys() if p not in req_body.get('properties', {}).keys()]:
                err_out += (f'For the function "{action}" you have included the improper parameter {hall} in your '
                            f'generated list of parameters. Please only use parameters that are given in the function '
                            f'definition.\n')

        return err_out
