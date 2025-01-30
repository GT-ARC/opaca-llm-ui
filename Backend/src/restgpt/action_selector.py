import json
from typing import Any, Dict, List, Tuple
import re
import logging

from langchain_core.language_models import BaseChatModel

from ..models import AgentMessage, LLMAgent

logger = logging.getLogger()

examples = [
    {"input": "Instruction: Book the desk with id 5.", "output": """
API Call: BookDesk;{"desk": 5}
API Response: Successfully booked the desk with id 5."""},
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
API Response: Shelf 3 is now closed."""}
]

ACTION_SELECTOR_PROMPT = """
You are an agent that outputs RESTful API calls to assist with instructions against an API. 
You will receive a list of known services. These services will include actions. 
Sometimes the action name includes the agent name as a prefix, indicated by two hyphens.
Sometimes these actions will also have descriptions to better explain what each action does. 
Your task will be to output a fitting API call consisting of an action name and the parameters belonging to that action. 
You can get an overview of the parameters to each action from the list. Parameters can also be required. If this is the 
case, you should always check if the given instructions include values to these parameters. If they do, use the values 
from the instruction as values to the parameters to the action. If not, you output the keyword "MISSING" as the first 
word of your output and after 
that an overview of all the required parameters that are missing values in the instructions to 
successfully call that action. If values for non-required parameters are missing, you can ignore 
them in your API call, but if they are present in the instruction, always include them. 
You are forbidden to generate values for all parameters on your own. Only use values that have been given in 
the instruction.
Remember that the values for parameters are not always obvious, since the query is produced by a human. For example, 
if you think the query calls for an action which requires the parameter "item", see if any part of the human query 
would fit the general description of an item in that context. If a user would want to add bananas to its grocer list, 
you should assume that the value for the item parameter should be set to banana.
If the parameter for an action is of type string, check if the instruction indicates what part of it should be used as 
string. For example, if the instruction tells you to set the title to title, you should use "title" as the value for
the title.
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

API Call: action_name;{"parameter_name": "value"}

You are forbidden to start your response with anything else than the phrases "API Call:" or "MISSING".

Here is the list you should use to create the API Call:
"""

ACTION_SELECTOR_PROMPT_SLIM = """
You output API calls. The format in which you should answer is as follows:

API Call: action_name;{"parameter_name": "value"}

You will replace action_name with the exact name of the most fitting action given in the user input.
Sometimes the action includes the agent name as a prefix, indicated by two hyphens, which you should also include.
After that, you output a semicolon and then you output the parameters for that action in a JSON format.
As values for the parameters you use the most fitting value from the user input. For example, if an action requires 
the parameter "room" as a string and the user input specified the room as "kitchen", you use "kitchen" as the 
value for the parameter "room". Make sure to use the correct data type for the parameters. Sometimes parameter values 
are not clearly specified in the request. Try to evaluate what the user might want you to use as a value in the context 
of the most fitting action. If you think a value for a required parameter for the most fitting action is missing, 
then you output the keyword "MISSING" and 
after that a brief explanation of what parameter is missing. For example, if the action requires the parameter 
"room" but there is no value in the user query for that parameter, output "MISSING" No value found for parameter
 "room". Do not evaluate whether the value for the parameter is valid or not.
All of your answers either start with "API Call: " or "MISSING".

Here is the list of actions. It includes the name of the action, a short description if one is available,
an overview of the parameters to call that action, and the definition of custom parameters, if used.
"""


class ActionSelector(LLMAgent):

    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Action Selector",
            llm=llm.bind(stop=self._stop),
            system_prompt=ACTION_SELECTOR_PROMPT,
        )

    @property
    def _stop(self):
        return "API Response: "

    @staticmethod
    def _check_missing(output: str):
        if re.search("MISSING", output):
            return True
        return False

    @staticmethod
    def _check_valid_action(action_plan: str, actions: List, use_agent_names: bool) -> str:
        err_out = ""

        # Check if exactly one semicolon was generated
        if len(action_plan.split(';')) != 2:
            return ("Your generated action call is not properly formatted. It should include exactly one action, "
                    "a semicolon and a list of parameters in json format.\n")

        action, parameters = action_plan.split(';')

        if use_agent_names:
            if len(action.split('--')) != 2:
                return "You need to include the agent name in your action name."
            _, action = action.split('--')

        # Check if the parameters are in a valid json format
        try:
            p_json = json.loads(parameters)
        except ValueError as e:
            return "Your generated parameters are not in a valid JSON format.\n"

        action_from_list = None
        for a in actions:
            if a.action_name == action:

                # Check if another action was already found by that name, if it was -> delete err msgs
                if action_from_list is not None:
                    err_out = ""

                action_from_list = a

                # Check if all required parameters are present
                for parameter in [p for p in action_from_list.params_in.keys()
                                  if action_from_list.params_in[p].required]:
                    if parameter not in p_json.keys():
                        err_out += (f'You have not included the required parameter {parameter} in '
                                    f'your generated list of parameters for the action {action}.\n')

                # Check if no parameter is hallucinated
                for parameter in p_json.keys():
                    if parameter not in [p for p in action_from_list.params_in.keys()]:
                        err_out += (f'You have included the improper parameter {parameter} in '
                                    f'your generated list of parameters. Please only use parameters '
                                    f'that are given in the action description.\n')

                if err_out == "":
                    return ""

        if not action_from_list:
            err_out += ("Your selected action does not exist. "
                        "Please only use actions from the provided list of actions.\n")
        return err_out

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]]
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, api_call, api_response) in enumerate(history):
            scratchpad += f'Instruction: {plan}\n'
            scratchpad += 'API Call: ' + api_call + "\n"
            scratchpad += self._stop + api_response + "\n"
        return scratchpad

    async def ainvoke(
            self,
            inputs: Dict[str, Any]
    ) -> List[AgentMessage]:
        responses = []
        scratchpad = self._construct_scratchpad(inputs["action_history"])
        action_list = ""
        for action in inputs["actions"]:
            action_list += action.selector_str(inputs['config']['use_agent_names']) + '\n'

        # Initial Action/Parameter generation
        self.system_prompt = (ACTION_SELECTOR_PROMPT_SLIM if inputs['config']['slim_prompts']['action_selector']
                              else ACTION_SELECTOR_PROMPT) + action_list
        self.examples = examples if inputs['config']['examples']['action_selector'] else []
        self.input_variables = ['input']
        self.message_template = scratchpad.replace("{", "{{").replace("}", "}}") + "{input}"

        result = await super().ainvoke({"input": inputs["plan"], "history": inputs["message_history"]}, inputs["websocket"])
        result.content = result.content.replace("API Call:", "").strip()

        # Add first agent message to responses
        responses.append(result)

        # Return if the input prompt is missing required parameter values
        if self._check_missing(result.content):
            return responses

        correction_limit = 1
        while (err_msg := self._check_valid_action(
                result.content, inputs["actions"], inputs["config"]["use_agent_names"])) != "" and correction_limit < 3:
            logger.info(f'API Selector: Correction needed for request \"{result.content}\"\nCause: {err_msg}')

            result = await super().ainvoke({"input": inputs["plan"] + err_msg, "history": inputs["message_history"]}, inputs["websocket"])
            result.content = result.content

            responses.append(result)

            if self._check_missing(result.content):
                return responses
            else:
                responses[-1].content = result.content.replace("API Call:", "").strip()

            correction_limit += 1

        return responses
