import asyncio
import json
import time
from typing import List

from pydantic import BaseModel

from .prompts import GENERATOR_PROMPT, EVALUATOR_TEMPLATE, OUTPUT_GENERATOR_TEMPLATE, \
    OUTPUT_GENERATOR_NO_TOOLS, FILE_EVALUATOR_SYSTEM_PROMPT, FILE_EVALUATOR_TEMPLATE, OUTPUT_GENERATOR_SYSTEM_PROMPT
from ..abstract_method import AbstractMethod
from ..models import QueryResponse, SessionData, ChatMessage, ConfigParameter, Chat, ToolCall
from ..utils import openapi_to_functions


class ToolLLMMethod(AbstractMethod):
    NAME = 'tool-llm'

    def __init__(self, session, websocket=None):
        super().__init__(session, websocket)

    class EvaluatorResponse(BaseModel):
        reason: str
        decision: str

    @classmethod
    def config_schema(cls):
        return {
            "tool_gen_model": cls.make_llm_config_param(name="Generator", description="Generating tool calls"),
            "tool_eval_model": cls.make_llm_config_param(name="Evaluator", description="Evaluating tool call results"),
            "output_model": cls.make_llm_config_param(name="Output", description="Generating the final output"),
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
                step=1
            ),
       }

    async def query_stream(self, message: str, chat: Chat) -> QueryResponse:

        # Initialize parameters
        tool_messages = []          # Internal messages between llm-components
        t_called = 0                # Track how many tools have been called in total
        called_tools = {}           # Formatted list of tool calls including their results
        c_it = 0                    # Current internal iteration
        should_continue = True      # Whether the internal iteration should continue or not
        no_tools = False            # If no tools were generated, the Output Generator will include available tools
        skip_chain = False          # Whether to skip the internal chain and go straight to the output generation

        # Initialize the response object
        response = QueryResponse()
        response.query = message

        # Use config set in session, if nothing was set yet, use default values
        config = self.session.config.get(self.NAME, self.default_config())
        max_iters = config["max_rounds"]

        # Get tools and transform them into the OpenAI Function Schema
        try:
            tools, error = openapi_to_functions(await self.session.opaca_client.get_actions_openapi(inline_refs=True))
        except AttributeError as e:
            response.error = str(e)
            response.content = "ERROR: It seems you are not connected to a running OPACA platform!"
            return response
        if len(tools) > 128:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
            tools = tools[:128]

        # Save time before execution
        total_exec_time = time.time()

        # If files were uploaded, check if any tools need to be called with extracted information
        if self.session.uploaded_files:
            result = await self.call_llm(
                model=config['tool_eval_model'],
                agent='Tool Evaluator',
                system_prompt=FILE_EVALUATOR_SYSTEM_PROMPT,
                messages=[
                    ChatMessage(role="user", content=FILE_EVALUATOR_TEMPLATE.format(
                        message=message,
                    )),
                ],
                response_format=self.EvaluatorResponse,
                temperature=config['temperature'],
                tools=tools,
                tool_choice="none",
            )
            response.agent_messages.append(result)
            try:
                formatted_result = json.loads(result.content)
                skip_chain = formatted_result["decision"] == 'FINISHED'
            except json.JSONDecodeError as e:
                print(f'Encountered error when parsing json content: {e}')

        # If no tools are available, skip the internal chain and go straight to the output generation
        if len(tools) == 0:
            skip_chain = True
            no_tools = True


        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < max_iters and not skip_chain:
            result = await self.call_llm(
                model=config['tool_gen_model'],
                agent='Tool Generator',
                system_prompt=GENERATOR_PROMPT,
                messages=[
                    *chat.messages,
                    ChatMessage(role="user", content=message),
                    *tool_messages,
                ],
                temperature=config['temperature'],
                tools=tools,
            )

            if not result.tools:
                no_tools = True
                break

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := self.check_valid_action(tools, result.tools)) and correction_limit < 3:
                full_err += err_msg
                result = await self.call_llm(
                    model=config['tool_gen_model'],
                    agent='Tool Generator',
                    system_prompt=GENERATOR_PROMPT,
                    messages=[
                        *chat.messages,
                        ChatMessage(role="user", content=message),
                        *tool_messages,
                        ChatMessage(role="user", content=full_err),
                    ],
                    temperature=config['temperature'],
                    tools=tools,
                )
                correction_limit += 1

            response.agent_messages.append(result)

            # Check if tools were generated and if so, execute them by calling the opaca-proxy
            tasks = []
            for i, call in enumerate(result.tools):
                tasks.append(self.invoke_tool(call.name, call.args, t_called))
                t_called += 1

            result.tools = await asyncio.gather(*tasks)

            # If a websocket was defined, send the tools WITH their results to the frontend
            if self.websocket:
                await self.websocket.send_json(result.model_dump_json())

            called_tools[c_it] = self._build_tool_desc(c_it, result.tools)

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tools) > 0:
                result = await self.call_llm(
                    model=config['tool_eval_model'],
                    agent='Tool Evaluator',
                    system_prompt='',
                    messages=[
                        ChatMessage(role="user", content=EVALUATOR_TEMPLATE.format(
                            message=message,
                            called_tools=called_tools,
                        )),
                    ],
                    response_format=self.EvaluatorResponse,
                    temperature=config['temperature'],
                    tools=tools,
                    tool_choice="none",
                )
                response.agent_messages.append(result)

                try:
                    formatted_result = json.loads(result.content)
                    should_continue = formatted_result["decision"] == 'CONTINUE'
                    result.content = formatted_result["reason"]
                except json.JSONDecodeError:
                    should_continue = False
                    result.content = "ERROR: The response from the Tool Evaluator was not in the correct format!"

                # Add generated response to internal history to give result to first llm agent
                tool_messages.append(ChatMessage(role="assistant", content=str(called_tools)))
                tool_messages.append(ChatMessage(role="user", content=f"Based on the called tools, another LLM has "
                                                                       f"decided to continue the process with the "
                                                                       f"following reason: {result.content}"))
            else:
                should_continue = False

            c_it += 1

        result = await self.call_llm(
            model=config['output_model'],
            agent='Output Generator',
            system_prompt=OUTPUT_GENERATOR_SYSTEM_PROMPT,
            messages=[
                *chat.messages,
                ChatMessage(role="user", content=OUTPUT_GENERATOR_NO_TOOLS.format(message=message) if no_tools else
                OUTPUT_GENERATOR_TEMPLATE.format(
                    message=message,
                    called_tools=called_tools or "",
                )),
            ],
            temperature=config['temperature'],
            tools=tools if no_tools else [],
            tool_choice="none",
        )
        response.agent_messages.append(result)

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        response.error = error
        return response

    @staticmethod
    def check_valid_action(tools, calls: List[ToolCall]) -> str:
        # Save all encountered errors in a single string, which will be given to the llm as an input
        err_out = ""

        # Since the gpt models can generate multiple tools, iterate over each generated call
        for call in calls:

            # Get the generated name and parameters
            action = call.name
            args = call.args

            # Check if the generated action name is found in the list of action definitions
            # If not, abort current iteration since no reference parameters can be found
            action_def = None
            for a in tools:
                if a['name'] == action:
                    action_def = a
            if not action_def:
                err_out += (f'Your generated function name "{action}" does not exist. Only use the exact function name '
                            f'defined in your tool section. Please make sure to separate the agent name and function '
                            f'name with two hyphens "--" if it is defined that way.\n')
                continue

            # Get the request body definition of the found action
            req_body = action_def['parameters']

            # Check if all required parameters are present
            if missing := [p for p in req_body.get('required', []) if p not in args.keys()]:
                err_out += f'For the function "{action}" you have not included the required parameters {missing}.\n'

            # Check if no parameter is hallucinated
            if hall := [p for p in args.keys() if p not in req_body.get('properties', {}).keys()]:
                err_out += (f'For the function "{action}" you have included the improper parameter {hall} in your '
                            f'generated list of parameters. Please only use parameters that are given in the function '
                            f'definition.\n')

        return err_out

    @staticmethod
    def _build_tool_desc(c_it: int, tools: List[ToolCall]):
        return {c_it: [{"name": tool.name, "parameters": tool.args, "result": tool.result} for tool in tools]}
