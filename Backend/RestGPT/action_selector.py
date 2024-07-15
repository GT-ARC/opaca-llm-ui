import json
from typing import Any, Dict, List, Tuple
import re
import logging

from langchain.chains.base import Chain

from .utils import OpacaLLM

logger = logging.getLogger()

examples = [
    {"input": "Instruction: Get the temperature for the room kitchen.", "output": """
API Call: GetTemperature;{"room": "kitchen"}
API Response: The temperature in the kitchen is 23 degrees."""},
    {"input": "Instruction: Book the desk with id 5.", "output": """
API Call: BookDesk;{"desk": 5}
API Response: Successfully booked the desk with id 5."""},
    {"input": "Instruction: Check if the desk with id 3 is free.", "output": """
API Call: IsFree;{"desk": 3}
API Response: The desk with id 3 is free."""},
    {"input": "Instruction: Check if the shelf with id 1 contains plates.", "output": """
API Call: GetContents;{"shelf": 1}
API Response: The shelf with id 1 contains plates."""},
    {"input": """
Instruction: Get a list of all desks ids for the office.
API Call: GetDesks;{}
API Response: Error: The action 'GetDesks' is not found. Please check the action name or the parameters used.
Instruction: CONTINUE""", "output": """
API Call: GetDesks;{"room": "office"}
API Response: The list of desks ids in the office room is (0, 1, 2, 3, 4, 5)."""},
    {"input": """
Instruction: Get all available shelf ids.
API Call: GetShelves;{}
API Response: The available shelves are (0, 1, 2, 3).
Instruction: Check if the shelf with id 3 has cups in it.
API Call: GetContents;{"shelf": 3}
API Response: The contents of shelf 3 are: plates, cups, and glasses.
Instruction: Close the shelf with id 3.""",
     "output": """
API Call: CloseShelf;{"shelf": 3}
API Response: Shelf 3 is now closed."""},
    {"input": """
Instruction Find the id of the shelf which contains the plates.
API Call: FindShelf;{"item": "plates"}
API Response: Your selected action does not exist. Pleas only use actions from the provided list of actions.""",
     "output": """
API Call: FindInShelf;{"item": "plates"}
API Response: The item "plates" can be found on shelf 3."""},
    {"input": """Instruction: Add an item to the grocery list.""", "output": """
MISSING The action to add an item to the grocery list "AddGroceries" requires the following parameters:
name: the name of the item
amount: the amount of those item
expirationDate: the expiration date of that item
category: The category of that item
However, these parameters were not found in the instruction."""}
]

ACTION_SELECTOR_PROMPT = """
You are an agent that outputs RESTful API calls to assist with instructions against an API. 
You will receive a list of known services. These services will include actions. 
Sometimes these actions will also have descriptions to better explain what each action does. 
Your task will be to output a fitting API call consisting of an action name and the parameters belonging to that action. 
You can get an overview of the parameters to each action from the list. Parameters can also be required. If this is the 
case, you should always check if the given instructions include values to these parameters. If they do, use the values 
from the instruction as values to the parameters to the action. If not, you output the keyword "MISSING" and after 
that an overview of all the required parameters that are missing values in the instructions to 
successfully call that action. If values for non-required parameters are missing, you can ignore 
them in your API call, but if they are present in the instruction, always include them. 
You are forbidden to generate values for all parameters on your own. Only use values that have been given in 
the instruction. 
If an action does not require parameters, just output an empty Json array like {}. 
Take note of the type of each parameter and output the value type accordingly. For example, if the type is string, 
the parameter you output needs to include quotation marks around the value. If the type is an integer, the value should 
just be a number without any quotation marks. You can follow the known OpenAPI schema for most of the types. 
If the type of the action is a custom type, the action should include the schema of the custom type. In that case, 
check if the instruction includes enough information to create the custom type and if it does, use it in your API call.
If it does not, output "MISSING" and after that a short summary of all the parameters for the custom type that are 
missing.
Do not use actions or parameters that are not included in the list. If there are no fitting actions in the list, 
output the keyword "MISSING" and after that a short summary explaining that there are no fitting actions available. 
If you think there is a fitting action, then your answer should only include the API 
call and the required parameters of that call, which will be included in a Json style format after the request URL. 
If you receive "CONTINUE" as an input, that means that your last API call was not successful. In this case you should 
modify the last call either by adding or removing parameters, correcting the type for specific parameters, or even try 
to call a different action.
Here is the format in which you should answer normally:

API Call: {action_name};{\"parameter_name\": \"value\"}

You are forbidden to start your response with anything else than the phrases "API Call:" or "MISSING".

Here is the list you should use to create the API Call:
"""


class ActionSelector(Chain):
    llm: OpacaLLM
    action_spec: List
    action_selector_prompt: str

    def __init__(self, llm: OpacaLLM, action_spec: List, action_selector_prompt=ACTION_SELECTOR_PROMPT) -> None:
        super().__init__(llm=llm, action_spec=action_spec, action_selector_prompt=action_selector_prompt)

    @property
    def _chain_type(self) -> str:
        return "Opaca-LLM Action Selector"

    @property
    def input_keys(self) -> List[str]:
        return ["plan"]

    @property
    def output_keys(self) -> List[str]:
        return ["result"]

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

    @staticmethod
    def _check_missing(output: str):
        if re.search("MISSING", output):
            return True
        return False

    @staticmethod
    def _check_valid_action(action_plan: str, actions: List) -> str:
        err_out = ""

        # Check if exactly one semicolon was generated
        if not len(action_plan.split(';')) == 2:
            err_out += ("Your generated action call is not properly formatted. It should include exactly one action, "
                        "a semicolon and a list of parameters in json format.\n")
            return err_out

        # Check if the action name is contained in the list of available actions and retrieve the action
        action, parameters = action_plan.split(';')
        action_from_list = None
        for a in actions:
            if a.action_name == action:
                action_from_list = a
        if not action_from_list:
            err_out += ("Your selected action does not exist. "
                        "Please only use actions from the provided list of actions.\n")
            return err_out

        # Check if all required parameters are present
        p_json = json.loads(parameters)
        for parameter in [p for p in action_from_list.params_in.keys()
                          if action_from_list.params_in[p].required]:
            if parameter not in p_json.keys():
                err_out += (f'You have not included the required parameter {parameter} in '
                            f'your generated list of parameters for the action {action}.\n')

        # Check if no parameter is hallucinated
        for parameter in p_json.keys():
            if parameter not in [p for p in action_from_list.params_in.keys()]:
                err_out += (f'You have included the improper parameter {parameter} in your generated list of '
                            f'parameters. Please only use parameters that are given in the action description.\n')
        return err_out

    @staticmethod
    def _construct_examples() -> str:
        example_str = ("Further you will receive a number of example conversations. You should not include these "
                       "examples as part of the actual message history of a user. Here are the examples:\n")
        for example in examples:
            example_str += f'Human: {example["input"]}\nAI: {example["output"]}\n'
        example_str += "These were all the examples, now the conversation with a real user begins.\n"
        return example_str

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]]
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, api_call, api_response) in enumerate(history):
            scratchpad += f'Instruction: {plan}\n'
            scratchpad += self.llm_prefix + api_call + "\n"
            scratchpad += self.observation_prefix + api_response + "\n"
        return scratchpad

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        scratchpad = self._construct_scratchpad(inputs["history"])
        example_list = self._construct_examples()
        action_list = ""
        for action in inputs["actions"]:
            action_list += action.selector_str()

        messages = [{"role": "system", "content": self.action_selector_prompt + action_list + example_list},
                    {"role": "human", "content": scratchpad + f'Instruction: {inputs["plan"]}'}]

        action_selector_output = self.llm.bind(stop=self._stop).call(messages)

        action_plan = re.sub(r"API Call+:", "", action_selector_output)

        if self._check_missing(action_plan):
            return {"result": action_plan}
        else:
            action_plan = action_plan.split('\n')[0].strip()

        correction_limit = 0
        while (err_msg := self._check_valid_action(action_plan, inputs["actions"])) != "" and correction_limit < 3:
            logger.info(f'API Selector: Correction needed for request {action_plan}\nCause: {err_msg}')
            messages.append({"role": "human", "content": err_msg})

            action_selector_output = self.llm.bind(stop=self._stop).call(messages)
            action_plan = re.sub(r"API Call:", "", action_selector_output).split('\n')[0].strip()

            correction_limit += 1

        return {"result": action_plan}
