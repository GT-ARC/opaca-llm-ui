import re
import time
from typing import List
import os

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .tool_method import ToolMethod
from ..models import Response, SessionData, OpacaLLMBackend, LLMAgent
from ..utils import openapi_to_functions, add_dicts, openapi_to_llama


TOOL_GENERATOR_PROMPT = """You are a helpful ai assistant that plans solution to user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. If other tool calls have been 
made already, you will receive the generated AI response of these tool calls. In that 
case you should continue to fulfill the user query with the additional knowledge. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services."""


class ToolLLMBackend(OpacaLLMBackend):
    max_iter: int = 5
    method: ToolMethod

    def __init__(self, method: str):
        self.method = ToolMethod.create_method(method)

    @property
    def default_config(self):
        return self.method.config

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
        config = session.config.get(self.method.name, self.default_config)

        # Save time before execution
        total_exec_time = time.time()

        """
        # Initialize model
        try:
            self.llm = self.method.init_model(config, session.api_key or os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            response.error = str(e)
            response.content = ("I am sorry, but I was unable to initialize the model for the selected method. "
                                "Make sure you use a valid API key.")
            return response

        # Get tools from connected opaca platform
        try:
            tools, error = self.method.get_tools(session.client.get_actions_with_refs(), config)
        except Exception as e:
            response.error += str(e)
            response.content = ("It appears no actions were returned by the Opaca Platform. Make sure you are "
                                "connected to the Opaca Runtime Platform and the platform contains at least one "
                                "action.")
            return response
        """

        self.method.init_agents(session, config)

        # Run until request is finished or maximum number of iterations is reached
        while should_continue and c_it < self.max_iter:
            result = self.method.invoke_generator(session, message, tool_responses) # TODO?
            """
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
            """
            res_meta_data = result.response_metadata

            # Check the generated tool calls for errors and regenerate them if necessary
            # Correction limit is set to 3 to check iteratively:
            # 1. Valid action name 2. Parameters were generated in the "requestBody" field 3. Parameter validity
            # These steps are sequentially dependent and require at most 3 steps
            correction_limit = 0
            full_err = '\n'
            while (err_msg := self.method.check_valid_action(result.tools)) and correction_limit < 3:
                full_err += err_msg
                result = self.method.invoke_generator(session, message, tool_responses, full_err)
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
                result = self.method.invoke_evaluator(
                    message,  # Original user query
                    tool_names,  # ALL the tools used so far
                    tool_params,  # ALL the parameters used for the tools
                    tool_results  # ALL the results from the opaca action calls
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
