from typing import Any, Dict, List, Tuple
import re
import logging

from langchain.chains.base import Chain
from langchain.prompts.prompt import PromptTemplate

from .utils import get_matched_action, OpacaLLM

logger = logging.getLogger()

examples = [
    {"input": "Instruction: Get the temperature of the room with id 2.", "output": """
API Call 1: GetTemperature;{"room": "2"}
API Response : The temperature in the room with id 2 is 23 degrees."""},
    {"input": "Instruction: Book the desk with id 5.", "output": """
API Call 1: BookDesk;{"desk": 5}
API Response 1: Successfully booked the desk with id 5."""},
    {"input": "Instruction: Check if the desk with id 3 is free.", "output": """
API Call 1: IsFree;{"desk": 3}
API Response 1: The desk with id 3 is free."""},
    {"input": "Instruction: Check if the shelf with id 1 contains plates.", "output": """
API Call 1: GetContents;{"shelf": 1}
API Response 1: The shelf with id 1 contains plates."""},
    {"input": """
Instruction: Get a list of all desks ids for the office.
API Call 1: GetDesks;{}
API Response 1: Error: The action 'GetDesks' is not found. Please check the action name or the parameters used.
Instruction: Continue""", "output": """
API Call 2: GetDesks;{"room": "office"}
API Response 2: The list of desks ids in the office room is (0, 1, 2, 3, 4, 5)."""},
    {"input": """
Instruction: Get all available shelf ids.
API Call 1: GetShelfs;{}
API Response 1: The available shelves are (0, 1, 2, 3).
Instruction: Check if the shelf with id 3 has cups in it.
API Call 2: GetContents;{"shelf": 3}
API Response 2: The contents of shelf 3 are: plates, cups, and glasses.
Instruction: Close the shelf with id 3.""",
     "output": """
API Call 3: CloseShelf;{"shelf": 3}
API Response 3: Shelf 3 is now closed."""},
]

ACTION_SELECTOR_PROMPT = """
You are a planner that plans a sequence of RESTful API calls to assist with user queries against an API. 
You will receive a list of known services. These services will include actions. Only use the exact action names from this list. 
Also use the description of each service to better understand what the action does, if such a description is available.
Create a valid HTTP request which would succeed when called. Your http requests will always be of the type POST. 
If an action requires further parameters, use the most fitting parameters from the user request. 
If an action requires a parameter but there were no suitable parameters in the user request, generate a fitting value 
for the missing required parameter field. For example, if you notice from the action list that the required parameter
"room" was not given in the user query, try to guess a valid value for this parameter based on its type.
If an action does not require parameters, just output an empty json array like {}.
Take note of the type of each parameter and output the type accordingly. For example, if the type is string, it should
include quotation marks around the value. If the type is an integer, it should just be a number without quotation marks.
If the type is a float, it should be a number without quotation mark and a floating point.
If you think there were no fitting parameters in the user request, just create imaginary values for them based on their names. 
Do not use actions or parameters that are not included in the list. If there are no fitting actions in the list, 
include within your response the absence of such an action. If the list is empty, include in your response that there 
are no available services at all. If you think there is a fitting action, then your answer should only include the API 
call and the required parameters of that call, which will be included in a json style format after the request url. 
If you receive "Continue" as an input, that means that your last API call was not successful. In this case you should 
modify the last call eiter by adding or removing parameters, changing the value for specific parameters, or even try 
to call a different action.
Your answer should only include the request url and the parameters in a JSON format, nothing else. Here is the format in which you should answer:

{action_name};{\"parameter_name\": \"value\"}

Here is the list you should use to create create the API Call
"""


class ActionSelector(Chain):
    llm: OpacaLLM
    action_spec: List
    action_selector_prompt: str
    output_key: str = "result"

    def __init__(self, llm: OpacaLLM, action_spec: List, action_selector_prompt=ACTION_SELECTOR_PROMPT) -> None:
        super().__init__(llm=llm, action_spec=action_spec, action_selector_prompt=action_selector_prompt)

    @property
    def _chain_type(self) -> str:
        return "LLama Action Selector for OPACA"

    @property
    def input_keys(self) -> List[str]:
        return ["plan"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "API Response {}: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "API Call {}: "

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
        for i, (plan, api_call, api_response) in enumerate(history):
            scratchpad += f'Instruction: {plan}\n'
            scratchpad += self.llm_prefix.format(i + 1) + api_call + "\n"
            scratchpad += self.observation_prefix.format(i + 1) + api_response + "\n"
        return scratchpad

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        scratchpad = self._construct_scratchpad(inputs["history"])
        action_list = ""
        for action in inputs["actions"]:
            action_list += "{" + action.__str__() + "}"
        action_list = re.sub(r"\{", "{{", action_list)
        action_list = re.sub(r"}", "}}", action_list)

        messages = [{"role": "system", "content": self.action_selector_prompt + action_list}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})
        messages.append({"role": "human", "content": scratchpad + f'Instruction: {inputs["plan"]}'})

        action_selector_output = self.llm.bind(stop=self._stop).call(messages)

        action_plan = re.sub(r"API Call \d+:", "", action_selector_output).strip()

        # TODO check if generated action actually exist and all required parameters are fulfilled

        logger.info(f"API Selector: {action_plan}")

        return {"result": action_plan}
