import asyncio
import json
import time
from typing import List

from pydantic import BaseModel

from .prompts import GENERATOR_PROMPT, EVALUATOR_TEMPLATE, OUTPUT_GENERATOR_TEMPLATE, \
    OUTPUT_GENERATOR_NO_TOOLS, FILE_EVALUATOR_SYSTEM_PROMPT, FILE_EVALUATOR_TEMPLATE, OUTPUT_GENERATOR_SYSTEM_PROMPT
from ..abstract_method import AbstractMethod
from ..models import QueryResponse, ChatMessage, Chat, ToolCall, MethodConfig


class ToolLlmConfig(MethodConfig):
    tool_gen_model: str = MethodConfig.llm_field(title='Generator', description='Generating tool calls')
    tool_eval_model: str = MethodConfig.llm_field(title='Evaluator', description='Evaluating tool call results', supports_structured_output=True)
    output_model: str = MethodConfig.llm_field(title='Output', description='Generating the final output')
    temperature: float = MethodConfig.temperature_field()
    max_rounds: int = MethodConfig.max_rounds_field()


class ToolLLMMethod(AbstractMethod):
    NAME = 'tool-llm'
    CONFIG = ToolLlmConfig

    def __init__(self, session, streaming=False, internal_tools=None):
        super().__init__(session, streaming, internal_tools)

    class EvaluatorResponse(BaseModel):
        reason: str
        decision: str

    async def query(self, message: str, chat: Chat) -> QueryResponse:

        # Initialize parameters
        tool_messages = []          # Internal messages between llm-components
        called_tools = {}           # Formatted list of tool calls including their results
        c_it = 0                    # Current internal iteration
        should_continue = True      # Whether the internal iteration should continue or not
        skip_chain = False          # Whether to skip the internal chain and go straight to the output generation
        eval_reason = ""            # Saves the last reason the Evaluator Agent output for its decision

        # Initialize the response object
        response = QueryResponse()
        response.query = message

        # Use config set in session, if nothing was set yet, use default values
        config: ToolLlmConfig = self.get_config()
        max_iters = config.max_rounds

        # Get tools and transform them into the OpenAI Function Schema
        tools, error = await self.get_tools()

        # Save time before execution
        total_exec_time = time.time()

        # If files were uploaded, check if any tools need to be called with extracted information
        if not all(f.suspended for f in self.session.uploaded_files.values()):
            result = await self.call_llm(
                model=config.tool_eval_model,
                agent='Tool Evaluator',
                system_prompt=FILE_EVALUATOR_SYSTEM_PROMPT,
                messages=[
                    ChatMessage(role="user", content=FILE_EVALUATOR_TEMPLATE.format(
                        message=message,
                    )),
                ],
                response_format=self.EvaluatorResponse,
                temperature=config.temperature,
                tools=tools,
                tool_choice="none",
                status_message="Checking if tools are needed",
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


        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < max_iters and not skip_chain:
            result = await self.call_llm(
                model=config.tool_gen_model,
                agent='Tool Generator',
                system_prompt=GENERATOR_PROMPT,
                messages=[
                    *chat.messages,
                    ChatMessage(role="user", content=message),
                    *tool_messages,
                ],
                temperature=config.temperature,
                tool_choice="only",
                tools=tools,
                status_message="Generating Tool Calls"
            )

            if not result.tools:
                break

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := await self.check_valid_action(result.tools)) and correction_limit < 3:
                full_err += err_msg
                result = await self.call_llm(
                    model=config.tool_gen_model,
                    agent='Tool Generator',
                    system_prompt=GENERATOR_PROMPT,
                    messages=[
                        *chat.messages,
                        ChatMessage(role="user", content=message),
                        *tool_messages,
                        ChatMessage(role="user", content=full_err),
                    ],
                    temperature=config.temperature,
                    tool_choice="only",
                    tools=tools,
                    status_message="Fixing Tool Calls"
                )
                correction_limit += 1

            response.agent_messages.append(result)

            # Check if opaca tools were generated and if so, execute them by calling the opaca-proxy
            tasks = []
            mcp_tools = []
            for i, call in enumerate(result.tools):
                if call.type == "opaca":
                    tasks.append(self.invoke_tool(call.name, call.args, call.id))
                elif call.type == "mcp":
                    mcp_tools.append(call)

            result.tools = await asyncio.gather(*tasks)
            result.tools.extend(mcp_tools)

            called_tools[c_it] = self._build_tool_desc(c_it, result.tools)

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tools) > 0:
                result = await self.call_llm(
                    model=config.tool_eval_model,
                    agent='Tool Evaluator',
                    system_prompt='',
                    messages=[
                        *chat.messages,
                        ChatMessage(role="user", content=EVALUATOR_TEMPLATE.format(
                            message=message,
                            called_tools=called_tools,
                        )),
                    ],
                    response_format=self.EvaluatorResponse,
                    temperature=config.temperature,
                    tools=tools,
                    tool_choice="none",
                    status_message="Evaluating Tool Call Results"
                )
                response.agent_messages.append(result)

                try:
                    formatted_result = json.loads(result.content)
                    should_continue = formatted_result["decision"] == 'CONTINUE'
                    eval_reason = formatted_result["reason"]
                except json.JSONDecodeError:
                    should_continue = False
                    eval_reason = "ERROR: The response from the Tool Evaluator was not in the correct format!"

                # Add generated response to internal history to give result to first llm agent
                tool_messages.append(ChatMessage(role="assistant", content=str(called_tools)))
                tool_messages.append(ChatMessage(role="user", content=f"Based on the called tools, another LLM has "
                                                                       f"decided to continue the process with the "
                                                                       f"following reason: {eval_reason}"))
            else:
                should_continue = False

            c_it += 1

        result = await self.call_llm(
            model=config.output_model,
            agent='Output Generator',
            system_prompt=OUTPUT_GENERATOR_SYSTEM_PROMPT,
            messages=[
                *chat.messages,
                ChatMessage(role="user", content=OUTPUT_GENERATOR_NO_TOOLS.format(message=message) if len(called_tools) == 0 else
                OUTPUT_GENERATOR_TEMPLATE.format(
                    message=message,
                    eval_reason=eval_reason,
                    called_tools=called_tools or "",
                )),
            ],
            temperature=config.temperature,
            tools=tools,
            tool_choice="none",
            status_message="Generating final output",
            is_output=True,
        )
        response.agent_messages.append(result)

        response.execution_time = time.time() - total_exec_time
        response.iterations = c_it
        response.content = result.content
        response.error = error
        return response

    async def check_valid_action(self, calls: List[ToolCall]) -> str:
        # Save all encountered errors in a single string, which will be given to the llm as an input
        err_out = ""

        # Get the list of available tools without mcp tools
        tools, _ = await self.get_tools(include_mcp=False)

        # Since the gpt models can generate multiple tools, iterate over each generated call
        for call in calls:

            # MCP Tools do not need a validation check
            if call.type == "mcp":
                continue

            # Get the generated name and parameters
            action = call.name
            args = call.args

            # Check if the generated action name is found in the list of action definitions
            # If not, abort current iteration since no reference parameters can be found
            action_def = next((a for a in tools if a['name'] == action), None)
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
        return {c_it: [tool.without_id() for tool in tools]}
