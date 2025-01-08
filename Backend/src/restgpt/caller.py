import json
import logging
from typing import Dict, Any

from langchain_core.language_models import BaseChatModel

from ..models import AgentMessage, LLMAgent

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
Your task will be to generate a response in natural language for a user including all relevant information.
If there was an error or the api call was unsuccessful, then also generate an appropriate output to inform the user 
about the error."""


class Caller(LLMAgent):

    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name='Caller',
            llm=llm,
            system_prompt=CALLER_PROMPT,
        )

    async def ainvoke(self, inputs: Dict[str, Any]) -> AgentMessage:
        api_plan = inputs['api_plan']
        try:
            action_name, params = api_plan.split(';')
            if inputs['config']['use_agent_names']:
                agent_name, action_name = action_name.split('--', maxsplit=1)
        except ValueError:
            return AgentMessage(
                agent="Caller",
                content='ERROR: Received malformed instruction by the action selector'
            )

        try:
            if inputs['config']['use_agent_names']:
                logger.info(f'Caller: Attempting to call http://localhost:8000/invoke/{agent_name}/{action_name} '
                            f'with parameters: {params}')
                response = inputs["client"].invoke_opaca_action(action_name, agent_name, json.loads(params))
            else:
                logger.info(f'Caller: Attempting to call http://localhost:8000/invoke/{action_name} '
                            f'with parameters: {params}')
                response = inputs["client"].invoke_opaca_action(action_name, None, json.loads(params))
        except Exception as e:
            return AgentMessage(
                agent="Caller",
                content=f'ERROR: Unable to call the connected opaca platform\nCause: {e}'
                )

        logger.info(f'Caller: Received response: {response}')

        description = ""
        # Get description from action list
        for action in inputs["actions"]:
            if action.action_name == action_name:
                description = action.description

        self.examples = examples if inputs['config']['examples']['caller'] else []
        self.input_variables = ["api_call", "description", "params", "response"]
        self.message_template = ("API Call: {api_call}\nDescription: {description}\n" 
                                 "Parameter: {params}\nResult: {response}")

        return await super().ainvoke({"api_call": action_name, "description": description,
                                      "params": params, "response": response})
