import json
import logging
from typing import Dict, List, Optional, Tuple, Any
import time
import re
import requests

from langchain.chains.base import Chain
from langchain_community.utilities import RequestsWrapper
from langchain.prompts.prompt import PromptTemplate

from ..opaca_proxy import proxy as opaca_proxy
from .utils import fix_json_error, OpacaLLM

logger = logging.getLogger(__name__)

examples = [
    {"input": """
API Call: http://localhost:8000/invoke/GetTemperature
Description: Get the current temperature for the room with the given room id.
Parameter: {"room": "1"}
Result: 23""", "output": "The temperature for room 1 is 23 degrees."},
    {"input": """
API Call: http://localhost:8000/invoke/IsFree
Description: Check if a given desk id is free and available to book.
Parameter: {"desk": 4}
Result: False""", "output": """The desk 4 is currently not free."""},
    {"input": """
API Call: http://localhost:8000/invoke/GetShelfs
Description: Returns a list of all available shelf ids.
Parameter: {}
Result: [0, 1, 2, 3]""", "output": """The available desks are (0, 1, 2, 3)"""},
    {"input": """
API Call: http://localhost:8000/invoke/NavigateTo
Description: Returns an instruction to navigate to the given room.
Parameter: {"room": "Kitchen"}
Result: Turn left, move to the end of the hallway, then enter the door on your right.""", "output": """
To navigate to the kitchen, you have to turn left, move to the end of the hallway, then enter the door on your right."""},
]

CALLER_PROMPT_ALT = """You are an agent that summarizes API calls.
You will be provided with an API call, which will include the endpoint that got called, a description for the API call if one is available, the parameters that were used for that API call, and finally the result that was returned after calling that API.
Your task will be to generate a response in natural language for a user.
If there was an error or the api call was unsuccessful, then also generate an appropriate output to inform the user about the error."""


class Caller(Chain):
    llm: OpacaLLM
    action_spec: List
    requests_wrapper: RequestsWrapper
    max_iterations: Optional[int] = 15
    max_execution_time: Optional[float] = None
    early_stopping_method: str = "force"
    simple_parser: bool = False
    with_response: bool = False
    output_key: str = "result"
    request_headers: Dict = None

    def __init__(self, llm: OpacaLLM, action_spec: List, requests_wrapper: RequestsWrapper,
                 simple_parser: bool = False, with_response: bool = False, request_headers: Dict = None) -> None:
        super().__init__(llm=llm, action_spec=action_spec, requests_wrapper=requests_wrapper,
                         simple_parser=simple_parser, with_response=with_response, request_headers=request_headers)

    @property
    def _chain_type(self) -> str:
        return "Opaca LLM Caller"

    @property
    def input_keys(self) -> List[str]:
        return ["api_plan"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
        if self.max_iterations is not None and iterations >= self.max_iterations:
            return False
        if (
                self.max_execution_time is not None
                and time_elapsed >= self.max_execution_time
        ):
            return False

        return True

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Thought: "

    @property
    def _stop(self) -> List[str]:
        return [
            f"\n{self.observation_prefix.rstrip()}",
            f"\n\t{self.observation_prefix.rstrip()}",
        ]

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]]
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, execution_res) in enumerate(history):
            scratchpad += self.llm_prefix.format(i + 1) + plan + "\n"
            scratchpad += self.observation_prefix + execution_res + "\n"
        return scratchpad

    def _get_action_and_input(self, llm_output: str) -> Tuple[str, str]:
        if "Execution Result:" in llm_output:
            return "Execution Result", llm_output.split("Execution Result:")[-1].strip()
        # \s matches against tab/newline/whitespace
        regex = r"Operation:[\s]*(.*?)[\n]*Input:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            # TODO: not match, just return
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        if action not in ["GET", "POST", "DELETE", "PUT"]:
            raise NotImplementedError

        # avoid error in the JSON format
        action_input = fix_json_error(action_input)

        return action, action_input

    def _get_response(self, action: str, action_input: str) -> str:
        action_input = action_input.strip().strip('`')
        left_bracket = action_input.find('{')
        right_bracket = action_input.rfind('}')
        action_input = action_input[left_bracket:right_bracket + 1]
        try:
            data = json.loads(action_input)
        except json.JSONDecodeError as e:
            raise e

        desc = data.get("description", "No description")
        query = data.get("output_instructions", None)

        params, request_body = None, None
        if action == "GET":
            if 'params' in data:
                params = data.get("params")
                response = self.requests_wrapper.get(data.get("url"), params=params)
            else:
                response = self.requests_wrapper.get(data.get("url"))
        elif action == "POST":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.post(data["url"], params=params, data=request_body)
        elif action == "PUT":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.put(data["url"], params=params, data=request_body)
        elif action == "DELETE":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.delete(data["url"], params=params, json=request_body)
        else:
            raise NotImplementedError

        if isinstance(response, requests.models.Response):
            if response.status_code != 200:
                return response.text
            response_text = response.text
        elif isinstance(response, str):
            response_text = response
        else:
            raise NotImplementedError

        return response_text, params, request_body, desc, query

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()
        intermediate_steps: List[Tuple[str, str]] = []

        api_plan = inputs['api_plan']
        try:
            api_call, params = api_plan.split(';')
        except:
            return {'result': 'ERROR: Received malformed instruction by the action selector'}
        logger.info(f'Caller: Attempting to call http://localhost:8000/invoke/{api_call} with parameters: {params}')

        try:
            response = opaca_proxy.invoke_opaca_action(api_call, None, json.loads(params))
        except:
            return {'result': 'ERROR: Unable to call the connected opaca platform'}

        description = ""
        # Get description from action list
        for action in inputs["actions"]:
            if action.name == api_call:
                description = action.description

        logger.info(f'Caller: Received response: {response}')

        messages = [{"role": "system", "content": CALLER_PROMPT_ALT}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})

        messages.append({"role": "human", "content": f"API Call: {api_call}\nDescription: {description}\nParameter: {params}\nResult: {response}"})

        caller_output = self.llm.call(messages)

        return {'result': caller_output}
