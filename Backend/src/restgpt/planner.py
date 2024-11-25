import logging
from typing import Any, Dict, List, Tuple
import re

from langchain.chains.base import Chain
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from .utils import build_prompt
from ..models import AgentMessage

logger = logging.getLogger()

examples = [
    {"input": "Book me the desk with id 6.", "output": """
Plan step 1: Check if the desk with id 6 is currently free.
API response: The desk with id 6 is free.
Plan step 2: Book the desk with id 6.
API response: Successfully booked the desk with id 6."""},
    {"input": "Can you open shelf 1 for me?", "output": """
Plan step 1: Open the shelf with id 1.
API response: The shelf with id 1 is now open."""},
    {"input": "Please open the shelf with cups in it.", "output": """
Plan step 1: Find the shelf with the cups in it.
API response: The shelf containing the cups is the shelf with id 3.
Plan step 2: Open the shelf with id 3.
API response: Successfully opened the shelf with id 3."""},
    {"input": "Book me any desk in the office that is currently free.", "output": """
Plan step 1: Get all desks in the office.
API response: The ids of the desks are 0, 4, 6.
Plan step 2: Check if the desk with id 0 is free.
API response: The desk with id 0 is not free.
Plan step 3: Check if the desk with id 4 is free.
API response: The desk with id 4 is free.
Plan step 4: Book the desk with id 4.
API response: Successfully booked the desk with id 4."""},
    {"input": "Show me the way to the kitchen.", "output": """
Plan step 1: Get the way to the kitchen.
API response: Turn left, move to the end of the hallway, then enter the door to the right to reach the kitchen."""},
    {"input": "Get the Co2 level for sensor 111 and the temperature for sensor 103.", "output": """
Plan step 1: Get the Co2 level for sensor 111.
API response: The Co2 level for sensor 111 is 39.0.
Plan step 2: Get the temperature for sensor 103.
API response: The humidity for room 1 is 45.2."""},
    {"input": "Please add 4 apples to my grocery list with an expiration date of 29th of July 2024", "output": """
Plan step 1: Add 4 apples to the grocery list with expiration date 29.07.2024 to the category fruits.
API response: Added 4 apples to the grocery list with category fruits and expiration date 29.07.2024"""},
    {"input": "Can you give me a list of all sensor ids?", "output": """
Plan step 1: Get a list of all sensor ids.
API response: Here is a list of all sensor ids: [100, 101, 104, 116, 205, 206]"""},
]


PLANNER_PROMPT = """You are an agent that plans solution to user queries.
Your task will be to transform a user query into a concrete plan step or even multiple plan steps if necessary, 
which can be solved by calling the services from the list you will be provided with. Each plan step will be used 
to call exactly one service. The division into multiple 
steps is only necessary if the query requires it. For example, if a user asks for multiple information which can 
only be gathered by calling multiple services, you should create a concrete plan step for each information. Each step 
you create will result in exactly one service call. The steps need to be as precise and clear as possible, and should 
always include all required parameters to call that service. You can get the list of required parameters for each 
action in the list of actions you will be provided. For example, if a user wants to get all desks in the office and the 
action to retrieve all desks requires the parameter room, you need to include "office" in your plan step. 
Be aware that users might not provide you with the exact name of a parameter or even include spelling mistakes. 
For example, if the service a user wants you to call 
requires an id and the user provides a number in its query, you should assume that the number is meant to represent 
the id parameters. Do not make up any 
parameters. As long as a parameter given by a user matches the type of the parameter, you can assume that the given 
parameter is valid. For example, if a service requires a number and the user has provided you with a number, you should 
assume that parameter as valid. 
Aside from you normal task to generate plan steps, you can also answer the user directly if the user 
query involves questions regarding the list of services. For example, if the user asks what services are available 
or asks about more information to specific services, you should then output the keyword "STOP" and after that keyword 
give an answer in natural language that will be directly returned to the user. Anytime you think that the user query 
is not executable, you should also output the keyword "STOP" and after that an explanation why you think the user query 
is not executable. If a user query might be executable but the user has not provided you with enough information about 
required parameters from the most fitting service, you also output the keyword "STOP" and after that ask the user 
to provide these missing parameters. Keep in mind that the user provides you the parameters in natural language.

You always follow this format:

Human: This is the query you have received from the user.
AI:
Plan step 1: This is the first step of your plan to fulfill the user query.
API response: This is the result of your first plan step.
Plan step 2: This is the second step of your plan.
API response: This the the result of your second plan step.
... (This schema can continue as long as necessary)

If an API response returns an error or unrelated information despite you giving clear instructions, you output the 
keyword "CONTINUE" to let the other agents know that they have made an error. 

In summary, your output starts either with "Plan", 
the keyword "STOP" or the keyword "CONTINUE". You are forbidden to put any other words except for those three at 
the beginning of your output.

Here is the list of services. The services include their name, a description if one is available, and an overview
of the parameters needed to call the service. Remember that your plan steps should be generated based on these 
services:
"""

PLANNER_PROMPT_SLIM = """
You plan solutions to user queries. A user will give you a question or instruction and you will output the next 
concrete step to solve this question or instruction. You will receive a list of available actions, some of which will 
include descriptions. You use these actions to formulate the steps. Some user queries can only be fulfilled with 
multiple steps. Sometimes to fulfill a query you need additional information, which can be retrieved by available 
actions. For example, if a query requires you to book a free desk, you first need to output a step to check if a given 
desk is free. Some actions will require parameters to be called. Always use the most fitting value from the user query 
as parameters in your steps. Make the value you want to use for a parameter very clear.
If you are certain the user has not provided you with all required parameters for service you want to call and you are 
unable to retrieve those parameters with actions, output the keyword "STOP" and ask the user for the remaining required parameters.
Once you receive a useful response for your step, continue with the next step.
If the user asks about more information about specific services or actions, you put the 
keyword "STOP" in front of your reply and answer the user directly. 
Never put the keyword "STOP" in your reply when your reply indicates that a service should be called.

A typical conversation where a user wants you to call services will look like this:

Human: The input from the user
AI:
Plan step 1: The first step of your plan.
API response: This is the result of your first plan step.
Plan step 2: The second step of your plan.
API response: This the the result of your second plan step.
... (This schema can continue as long as necessary)

Following is the list of available actions. It will include the name of each action, a description if one is 
available, and the parameters required to call that action.
"""


class Planner(Chain):
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(llm=llm)

    @property
    def _chain_type(self) -> str:
        return "Opaca-LLM Planner"

    @property
    def input_keys(self) -> List[str]:
        return ["input"]

    @property
    def output_keys(self) -> List[str]:
        return ["result"]

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "API response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Plan step {}: "

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
            scratchpad += self.observation_prefix + "\n"
        return scratchpad

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        scratchpad = self._construct_scratchpad(inputs['planner_history'])
        action_list = ""

        for action in inputs["actions"]:
            action_list += action.planner_str(inputs['config']['use_agent_names']) + '\n'

        prompt = build_prompt(
            system_prompt=(PLANNER_PROMPT_SLIM if inputs['config']['slim_prompts'] else PLANNER_PROMPT) + action_list,
            examples=examples if inputs['config']['examples']['planner'] else [],
            input_variables=["input"],
            message_template="{input}" + scratchpad
        )

        chain = prompt | self.llm.bind(stop=self._stop)

        output = chain.invoke({"input": inputs["input"], "history": inputs["message_history"]})

        # Checks if answer was generated by integrated model class or Llama proxy
        res_meta_data = {}
        if isinstance(output, AIMessage):
            res_meta_data = output.response_metadata.get("token_usage", {})
            output = output.content

        output = re.sub(r"Plan step \d+: ", "", output).strip()

        return {"result": AgentMessage(
            agent="Planner",
            content=output,
            response_metadata=res_meta_data,
        )}
