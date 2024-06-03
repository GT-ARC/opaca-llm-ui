import logging
from typing import Any, Dict, List, Tuple
import re

from langchain.chains.base import Chain

from .utils import OpacaLLM

logger = logging.getLogger()

examples = [
    {"input": "What is the current temperature in room 1?", "output": """
Plan step 1: Get the temperature in room 1.
API response: The temperature in room 1 is 23 degrees."""},
    {"input": "Book me the desk with id 6.", "output": """
Plan step 1: Check if the desk with id 6 is currently free.
API response: The desk with id 6 is free.
Plan step 2: Book the desk with id 6.
API response: Successfully booked the desk with id 6."""},
    {"input": "Please open the shelf with cups in it.", "output": """
Plan step 1: Get all available shelf ids.
API response: The available shelf ids are 0, 1, 2, 3.
Plan step 2: Check if the shelf with id 0 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 3: Check if the shelf with id 1 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 4: Check if the shelf with id 2 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 5: Check if the shelf with id 3 has cups in it.
API response: The shelf with id 0 does contain cups.
Plan step 6: Open the shelf with id 3.
API response: Successfully opened the shelf with id 3."""},
    {"input": "Book me any desk that is currently free.", "output": """
Plan step 1: Get all desks.
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
    {"input": "Get the noise and humidity for room 1 and the temperature for room 2.", "output": """
Plan step 1: Get the noise for room 1.
API response: The noise for room 1 is 39.0.
Plan step 2: Get the humidity for room 1.
API response: The humidity for room 1 is 45.2.
Plan step 3: Get the temperature for room 2.
API response: The temperature for room 2 is 22."""}
]

icl_examples = {
    "opaca": """Example 1:
User query: What is the current temperature in room 1?
Plan step 1: Get the temperature in room 1.
API response: The temperature in room 1 is 23 degrees.

Example 2:
User query: Book me the desk with id 6.
Plan step 1: Check if the desk with id 6 is currently free.
API response: The desk with id 6 is free.
Plan step 2: Book the desk with id 6.
API response: Successfully booked the desk with id 6.

Example 3:
User query: Please open the shelf with cups in it.
Plan step 1: Get all available shelf ids.
API response: The available shelf ids are 0, 1, 2, 3.
Plan step 2: Check if the shelf with id 0 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 3: Check if the shelf with id 1 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 4: Check if the shelf with id 2 has cups in it.
API response: The shelf with id 0 does not contain cups.
Plan step 5: Check if the shelf with id 3 has cups in it.
API response: The shelf with id 0 does contain cups.
Plan step 6: Open the shelf with id 3.
API response: Successfully opened the shelf with id 3.

Example 4:
User query: Book me any desk that is currently free.
Plan step 1: Get all desks.
API response: The ids of the desks are 0, 4, 6.
Plan step 2: Check if the desk with id 0 is free.
API response: The desk with id 0 is not free.
Plan step 3: Check if the desk with id 4 is free.
API response: The desk with id 4 is free.
Plan step 4: Book the desk with id 4.
API response: Successfully booked the desk with id 4.

Example 5:
User query: Show me the way to the kitchen.
Plan step 1: Get the way to the kitchen.
API response: Turn left, move to the end of the hallway, then enter the door to the right to reach the kitchen."""

}

PLANNER_PROMPT = """You are an agent that plans solution to user queries.
You should always give your plan in natural language.
Another model will receive your plan and find the right API calls and give you the result in natural language.
You will receive a list of services on which you can base your plan.
If you assess that the current plan has not been fulfilled, you can output "Continue" to let the API selector select another API to fulfill the plan.
In most case, search, filter, and sort should be completed in a single step.
The plan should be as specific as possible. It is better not to use pronouns in plan, but to use the corresponding results obtained previously. For example, instead of "Get the most popular movie directed by this person", you should output "Get the most popular movie directed by Martin Scorsese (1032)". If you want to iteratively query something about items in a list, then the list and the elements in the list should also appear in your plan.
The plan should be straightforward. If you want to search, sort or filter, you can put the condition in your plan. For example, if the query is "Who is the lead actor of In the Mood for Love (id 843)", instead of "get the list of actors of In the Mood for Love", you should output "get the lead actor of In the Mood for Love (843)".
If a query can only be solved in multiple steps, you should split your plan in multiple steps as well. For example, if a user request multiple data which can only be retrieved in multiple steps, you should only try and retrieve one information at once and then wait for the next step to retrieve the next information and so on.

Starting below, you should follow this format:

User query: The query a User wants help with related to the agent actions.
Plan step 1: The first step of your plan for how to solve the query.
API response: The result of the first step of your plan.
Plan step 2: If necessary, the second step of your plan for how to solve the query based on the API response.
API response: The result of the second step of your plan.
... (this Plan step n and API response can repeat N times)

Here are the list of services:
"""


class Planner(Chain):
    llm: OpacaLLM
    planner_prompt: str
    output_key: str = "result"

    def __init__(self, llm: OpacaLLM, planner_prompt=PLANNER_PROMPT) -> None:
        super().__init__(llm=llm, planner_prompt=planner_prompt)

    @property
    def _chain_type(self) -> str:
        return "LLama Planner"

    @property
    def input_keys(self) -> List[str]:
        return ["input"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

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
            scratchpad += self.observation_prefix + execution_res + "\n"
        return scratchpad

    def _call(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        scratchpad = self._construct_scratchpad(inputs['history'])
        action_list = ""

        for action in inputs["actions"]:
            action_list += "{" + action.__str__() + "}"
        action_list = re.sub(r"\{", "{{", action_list)
        action_list = re.sub(r"}", "}}", action_list)

        messages = [{"role": "system", "content": PLANNER_PROMPT + action_list}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})
        messages.append({"role": "human", "content": inputs["input"] + scratchpad})
        planner_chain_output = self.llm.bind(stop=self._stop).call(messages)

        planner_chain_output = re.sub(r"Plan step \d+: ", "", planner_chain_output).strip()

        return {"result": planner_chain_output}
