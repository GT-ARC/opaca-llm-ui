import re
from typing import List, Dict, Any, Tuple

from langchain.chains.base import Chain

from .utils import OpacaLLM


examples = [
    {"input": """
User query: What is the current temperature in room 1?
Plan step 1: Get the temperature in room 1.
API call 1: http://localhost:8000/invoke/GetTemperature;{"room": "1"}
API response 1: The temperature for room 1 is 23.0 degrees.""",
     "output": "FINISHED: The current temperature in room 1 is 23.0 degrees."},
    {"input": """
User query: Open the shelf that contains plates.
Plan step 1: Get a list of all available shelfs.
API call 1: http://localhost:8000/invoke/GetShelfs;{}
API response 1: The ids of all available shelfs are (0, 1, 2, 3)
Plan step 2: Check if shelf 0 contains plates.
API call 2: http://localhost:8000/invoke/GetContents;{"shelf": "0"}
API response 2: The shelf 0 contains plates, cups and glasses.""",
     "output": "CONTINUE"},
    {"input": """
User query: Open the shelf that contains plates.
Plan step 1: Get a list of all available shelfs.
API call 1: http://localhost:8000/invoke/GetShelfs;{}
API response 1: The ids of all available shelfs are (0, 1, 2, 3)
Plan step 2: Check if shelf 0 contains plates.
API call 2: http://localhost:8000/invoke/GetContents;{"shelf": 0}
API response 2: The shelf 0 contains plates, cups and glasses.
Plan step 3: Open shelf 0.
API call 3: http://localhost:8000/invoke/OpenShelf;{"shelf": 0}
API response 3: Opened shelf with id 0.""",
     "output": "FINISHED: I have found shelf 0 containing plates and opened it as you requested."},
    {"input": """
User query: Check if the desk with id 4 is currently free.
Plan step 1: Check if desk with id 4 is free.
API call 1: http://localhost:8000/invoke/IsFree;{"desk": 4}
API response 1: The desk with id 4 is currently not free.""",
     "output": "FINISHED: The desk with id 4 is not currently not free and unavailable to book."},
    {"input": """
User query: Show me the way to the kitchen.
Plan step 1: Get the navigation to the kitchen.
API call 1: http://localhost:8000/invoke/NavigateTo;{"room": "kitchen"}""",
     "output": "CONTINUE"},
    {"input": """
User query: Is the humidity in room 2 or 3 greater?
Plan step 1: Get the humidity of room 2.
API call 1: http://localhost:8000/invoke/GetHumidity;{"room": "2"}
API response 1: The humidity in room 2 is 0.36.
Plan step 2: Get the humidity of room 3.
API call 2: http://localhost:8000/invoke/GetHumidity;{"room": "3"}
API response 2: The humidity in room 3 is 0.38.""",
     "output": "FINISHED: The humidity in room 2 is 0.36 while the humidity in room 3 is 0.38. \
     Therefore, the humidity in room 3 is greater."},
    {"input": """
User query: Can you open the shelf with the plates in it for me?
Plan step 1: Get all available shelf ids.
API call 1: http://localhost:8000/invoke/GetShelfs;{}
API response 1: The available shelfs are (0, 1, 2, 3).
Plan step 2: Find the shelf with the plates.
API call 2: http://localhost:8000/invoke/FindInShelf;{"item": "plates"}
API response 2: The shelf containing the plates is shelf 3.""",
     "output": "CONTINUE"},
    {"input": """
User query: Can you open the shelf with the plates in it for me?
Plan step 1: Get all available shelf ids.
API call 1: http://localhost:8000/invoke/GetShelfs;{}
API response 1: The available shelfs are (0, 1, 2, 3).
Plan step 2: Find the shelf with the plates.
API call 2: http://localhost:8000/invoke/FindInShelf;{"item": "plates"}
API response 2: The shelf containing the plates is shelf 3.
Plan step 3: Open shelf 3.
API call 3: http://localhost:8000/invoke/OpenShelf;{"shelf": 3}
API response 3: The shelf with id 3 is now opened.""",
     "output": "FINISHED: I have located the plates in shelf 3 and opened this shelf as you have instructed me."},
    {"input": """
User query: Book me a free desk in the office?
Plan step 1: Get all desks in the office room.
API call 1: http://localhost:8000/invoke/GetDesks;{"room": "office"}
API response 1: The available desks in the office are (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10).
Plan step 2: Check if the desk with id 0 is free.
API call 2: http://localhost:8000/invoke/IsFree;{"desk": 0}
API response 2: The desk 0 is currently free.""",
     "output": "CONTINUE"},
    {"input": """What is the way to the kitchen?
Plan step 1: Get the way to the kitchen.
API call 1: http://localhost:8000/NavigateTo;{"room": "kitchen"}
API response 1: To navigate to the kitchen, you have to turn right, move to the end of the hallway, then enter to door to the left.""",
     "output": "FINISHED: To navigate to the kitchen, you have to turn right, move to the end of the hallway, then enter to door to the left."},
]


EVAL_PROMPT = """You are an evaluator.
Your task will be to analyze a chain of API calls and their responses.
If you deem that the user query has been fulfilled completely, which is at the top of each chain, you output "FINISHED" 
and after that a summary of the executed steps for the user. Be aware that your response is the only answer a user will 
receive, so always include relevant information to the user query in your response.
If a query requires searching, filtering, sorting and so on, the query is still only then fulfilled if the core intent 
of the query has been dealt with. For example, if a user wants to book a free desk, the query is only then fulfilled 
if a free desk was booked, not when a free desk was found or is available.
If you think that the user query is still unfulfilled, you output "CONTINUE".
If the query involves comparing results from different API calls and you determine that all necessary calls were made, 
you should output "FINISHED" as well followed with the result of such a comparison in natural language for the user."""


class Evaluator(Chain):
    llm: OpacaLLM
    planner_prompt: str
    output_key: str = "result"

    def __init__(self, llm: OpacaLLM, planner_prompt=EVAL_PROMPT) -> None:
        super().__init__(llm=llm, planner_prompt=planner_prompt)

    @property
    def _chain_type(self) -> str:
        return "LLama Evaluator"

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

        messages = [{"role": "system", "content": EVAL_PROMPT}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})
        messages.append({"role": "human", "content": inputs["input"]})
        eval_output = self.llm.call(messages)

        return {"result": eval_output}
