import json
import logging
from typing import Dict, List, Any

from langchain.chains.base import Chain

from ..opaca_proxy import proxy as opaca_proxy
from .utils import OpacaLLM, build_prompt

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
To navigate to the kitchen, you have to turn left, move to the end of the hallway, then enter the door on your right.
"""},
]

CALLER_PROMPT = """You are an agent that summarizes API calls.
You will be provided with an API call, which will include the endpoint that got called, a description for the API call 
if one is available, the parameters that were used for that API call, and finally the result that was returned after 
calling that API.
Your task will be to generate a response in natural language for a user.
If there was an error or the api call was unsuccessful, then also generate an appropriate output to inform the user 
about the error."""


class Caller(Chain):
    llm: OpacaLLM
    action_spec: List

    def __init__(self, llm: OpacaLLM, action_spec: List) -> None:
        super().__init__(llm=llm, action_spec=action_spec)

    @property
    def _chain_type(self) -> str:
        return "Opaca-LLM Caller"

    @property
    def input_keys(self) -> List[str]:
        return ["api_plan"]

    @property
    def output_keys(self) -> List[str]:
        return ["result"]

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        api_plan = inputs['api_plan']
        try:
            api_call, params = api_plan.split(';')
        except ValueError:
            return {'result': 'ERROR: Received malformed instruction by the action selector'}
        logger.info(f'Caller: Attempting to call http://localhost:8000/invoke/{api_call} with parameters: {params}')

        try:
            response = opaca_proxy.invoke_opaca_action(api_call, None, json.loads(params))
        except Exception as e:
            return {'result': f'ERROR: Unable to call the connected opaca platform\nCause: {e}'}

        logger.info(f'Caller: Received response: {response}')

        description = ""
        # Get description from action list
        for action in inputs["actions"]:
            if action.action_name == api_call:
                description = action.description

        prompt = build_prompt(
            system_prompt=CALLER_PROMPT,
            examples=examples,
            input_variables=["api_call", "description", "params", "response"],
            message_template="API Call: {api_call}\nDescription: {description}\n"
                             "Parameter: {params}\nResult: {response}"
        )

        chain = prompt | self.llm

        output = chain.invoke({"api_call": api_call, "description": description,
                               "params": params, "response": response})

        return {'result': output}
