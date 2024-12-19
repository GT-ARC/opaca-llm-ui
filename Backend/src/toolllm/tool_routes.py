import re
import time
from typing import List
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .tool_agents import ToolGenerator, ToolEvaluator
from ..models import Response, SessionData, OpacaLLMBackend
from ..toolllama import OpacaLLM
from ..utils import openapi_to_functions, add_dicts, openapi_to_llama


class ToolLLMBackend(OpacaLLMBackend):
    NAME_OPENAI = 'tool-llm-openai'
    NAME_LLAMA = 'tool-llm-llama'
    llm: BaseChatModel | ChatOpenAI
    max_iter: int = 5

    def __init__(self, use_llama: bool):
        self.use_llama = use_llama

    @property
    def _name(self):
        return self.NAME_LLAMA if self.use_llama else self.NAME_OPENAI

    @property
    def config(self):
        if self.use_llama:
            return {
                "llama-url": "http://10.0.64.101:11000",
                "llama-model": "llama3.1:70b",
                "temperature": 0,
                "use_agent_names": True,
                "max_iterations": 5
            }
        else:
            return {
                "gpt_model": "gpt-4o-mini",
                "temperature": 0,
                "use_agent_names": True,
            }

    async def query(self, message: str, session: SessionData) -> Response:

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
        config = session.config.get(self._name, self.config)

        # Save time before execution
        total_exec_time = time.time()

        # Initialize selected model
        if self.use_llama:
            self.llm = OpacaLLM(url=config['llama-url'], model=config['llama-model'])
        else:
            try:
                self.init_model(session.api_key, config)
            except ValueError as e:
                response.error = str(e)
                response.content = ("You are trying to use a model which uses an api key but provided none. Please "
                                    "enter a valid api key and try again.")
                return response

        # Get tools from connected opaca platform
        try:
            if self.use_llama:
                tools, error = openapi_to_llama(session.client.get_actions_with_refs(), config['use_agent_names'])
                tools = [{"type": "function", "function": tool} for tool in tools]
            else:
                # Convert openapi schema to openai function schema
                tools, error = openapi_to_functions(session.client.get_actions_with_refs(), config['use_agent_names'])
                if len(tools) > 128:
                    tools = tools[:128]
                    error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                              f"of 128. All tools after index 128 will be ignored!\n")
            response.error += error
        except Exception as e:
            response.error += str(e)
            response.content = ("It appears no actions were returned by the Opaca Platform. Make sure you are "
                                "connected to the Opaca Runtime Platform and the platform contains at least one "
                                "action.")
            return response

        generator_agent = ToolGenerator(
            self.llm,
            tools=tools,
            input_variables=['input', 'history', 'config'] if self.use_llama else ['input', 'scratchpad'],
            message_template='' if self.use_llama else 'Human: {input}{scratchpad}',
        )
        evaluator_agent = ToolEvaluator(self.llm, tools=tools)

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:
            if self.use_llama:
                result = generator_agent.invoke({
                    'input': message,
                    'config': config,
                    'history': session.messages,
                })
            else:
                result = generator_agent.invoke({
                    'input': message,
                    'scratchpad': self.build_scratchpad(tool_responses),  # scratchpad contains ai responses
                    'history': session.messages
                })
            res_meta_data = result.response_metadata

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := self._check_valid_action(result.tools, tools[:128])) and correction_limit < 3:
                full_err += err_msg
                result = generator_agent.invoke({
                    'input': message,
                    'scratchpad': self.build_scratchpad(tool_responses) + full_err,
                    'history': session.messages
                })
                res_meta_data = add_dicts(result.response_metadata.get("token_usage", {}), res_meta_data)
                correction_limit += 1

            response.agent_messages.append(result)

            # Check if tools were generated and if so, execute them by calling the opaca-proxy
            for call in result.tools.copy():

                tool_names.append(call['name'])
                tool_params.append(call['args'])
                try:
                    if config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    tool_results.append(
                        session.client.invoke_opaca_action(
                            action_name,
                            agent_name,
                            call['args']['requestBody'] if 'requestBody' in call['args'] else {}
                        ))
                except Exception as e:
                    tool_results.append(str(e))
                response.agent_messages[-1].tools.append(f'Tool {len(tool_names)}: '
                                                         f'{call["name"]}, '
                                                         f'{call["args"]["requestBody"] if "requestBody" in call["args"] else {} }, '
                                                         f'{tool_results[-1]}\n')

            # If tools were created, summarize their result in natural language
            # either for the user or for the first model for better understanding
            if len(result.tools) > 0:
                result = evaluator_agent.invoke({
                    'query': message,  # Original user query
                    'tool_names': tool_names,  # ALL the tools used so far
                    'parameters': tool_params,  # ALL the parameters used for the tools
                    'results': tool_results  # ALL the results from the opaca action calls
                })
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

    def init_model(self, api_key: str, config: dict):
        api_key = api_key or os.getenv("OPENAI_API_KEY")  # if empty, use from Env
        self.check_for_key(api_key)
        self.llm = ChatOpenAI(
            model=config["gpt_model"],
            temperature=float(config["temperature"]),
            openai_api_key=api_key
        )

    @staticmethod
    def check_for_key(api_key: str):
        if not api_key:
            raise ValueError("No api key provided")

    @staticmethod
    def build_scratchpad(messages: List[AIMessage]) -> str:
        out = ''
        for message in messages:
            out += f'\nAI: {message.content}'
        return out

    @staticmethod
    def _check_valid_action(calls: List[dict], actions: List) -> str:
        # Save all encountered errors in a single string, which will be given to the llm as an input
        err_out = ""

        # Since the gpt models can generate multiple tools, iterate over each generated call
        for call in calls:

            # Get the generated name and parameters
            action = call['name']
            args = call['args'].get('requestBody', {})

            # Check if the generated action name is found in the list of action definitions
            # If not, abort current iteration since no reference parameters can be found
            action_def = None
            for a in actions:
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
