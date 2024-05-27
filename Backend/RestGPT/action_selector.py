from typing import Any, Dict, List, Tuple
import re
import logging

from langchain.chains.base import Chain
from langchain.prompts.prompt import PromptTemplate

from .utils import get_matched_action, OpacaLLM

logger = logging.getLogger()

examples = [
    {"input": "Get the temperature of the room with id 2.", "output": """
API call: GetTemperature;{"room": "2"}
API response: The temperature in the room with id 2 is 23 degrees."""},
    {"input": "Book the desk with id 5.", "output": """
API call: BookDesk;{"desk": 5}
API response: Successfully booked the desk with id 5."""},
    {"input": "Check if the desk with id 3 is free.", "output": """
API call: IsFree;{"desk": 3}
API response: The desk with id 3 is free."""},
    {"input": "Check if the shelf with id 1 contains plates.", "output": """
API call: GetContents;{"shelf": 1}
API response: The shelf with id 1 contains plates."""},
]

ACTION_SELECTOR_PROMPT = """
You are a planner that plans a sequence of RESTful API calls to assist with user queries against an API. 
You will receive a list of known services. These services will include actions. Only use the exact action names from this list. 
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
Your answer should only include the request url and the parameters in a JSON format, nothing else. Here is the format in which you should answer:

{action_name};{\"parameter_name\": \"value\"}

Here is the list you should use to create create the API call
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
        return ["plan", "background"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "API Response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "API Call: "

    @property
    def _stop(self) -> List[str]:
        return [
            f"\n{self.observation_prefix.rstrip()}",
            f"\n\t{self.observation_prefix.rstrip()}",
        ]

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]], instruction: str
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, api_plan, execution_res) in enumerate(history):
            if i != 0:
                scratchpad += "Instruction: " + plan + "\n"
            scratchpad += self.llm_prefix.format(i + 1) + api_plan + "\n"
            scratchpad += self.observation_prefix + execution_res + "\n"
        scratchpad += "Instruction: " + instruction + "\n"
        return scratchpad

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        action_list = ""
        for action in inputs["actions"]:
            action_list += "{" + action.__str__() + "}"
        action_list = re.sub(r"\{", "{{", action_list)
        action_list = re.sub(r"}", "}}", action_list)

        messages = [{"role": "system", "content": self.action_selector_prompt + action_list}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})
        messages.append({"role": "human", "content": inputs["plan"]})

        action_selector_output = self.llm.bind(stop=self._stop).call(messages)

        action_plan = re.sub(r"API call:", "", action_selector_output).strip()

        """
        finish = re.match(r"No Action needed.(.*)", action_plan)
        if finish is not None:
            return {"result": action_plan}

        while get_matched_action(self.action_spec, action_plan) is None:
            logger.info(
                "API Selector: The action you called is not in the list of available action. Please use another action.")
            scratchpad += action_selector_output + "\nThe action you called is not in the list of available actions. Please use another action.\n"
            action_selector_chain_output = action_selector_chain.invoke({"plan": inputs['plan'], "background": inputs['background'],
                                                                         "agent_scratchpad": scratchpad})
            action_plan = re.sub(r"API Call \d+: ", "", action_selector_chain_output).strip()
            logger.info(f"API Selector: {action_plan}")

        """
        logger.info(f"API Selector: {action_plan}")

        return {"result": action_plan}
