from typing import List, Dict, Any, Tuple

from langchain_core.language_models import BaseChatModel

from ..models import AgentMessage, LLMAgent

examples = [
    {"input": """What is the way to the kitchen?
Plan step 1: Get the way to the kitchen.
API call 1: http://localhost:8000/NavigateTo;{"room": "kitchen"}
API response 1: To navigate to the kitchen, you have to turn right, move to the end of the hallway, 
then enter to door to the left.""",
     "output": "FINISHED To navigate to the kitchen, you have to turn right, "
               "move to the end of the hallway, then enter to door to the left."},
    {"input": """
User query: Book me a free desk in the office?
Plan step 1: Get all desks in the office room.
API call 1: http://localhost:8000/invoke/GetDesks;{"room": "office"}
API response 1: The available desks in the office are (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10).
Plan step 2: Check if the desk with id 0 is free.
API call 2: http://localhost:8000/invoke/IsFree;{"desk": 0}
API response 2: The desk 0 is currently free.
Plan step 3: Book the desk with id 0.
API call 3: http://localhost:8000/invoke/BookDesk;{"desk": 0}
API response 3: The desk 0 has been successfully booked.
    """,
     "output": "FINISHED I have checked the office for free desks and found that desk 0 was free. I have then"
               "booked desk 0 for you."},
    {"input": """
User query: Can you open the shelf with the plates in it for me?
Plan step 1: Find the shelf with the plates.
API call 1: http://localhost:8000/invoke/FindInShelf;{"item": "plates"}
API response 1: The shelf containing the plates is shelf 3.
Plan step 2: Open shelf 3.
API call 2: http://localhost:8000/invoke/OpenShelf;{"shelf": 3}
API response 2: The shelf with id 3 is now opened.""",
     "output": "FINISHED I have located the plates in shelf 3 and opened this shelf as you have instructed me."},
]


EVAL_PROMPT = """You are an evaluator.
Your task will be to analyze a chain of API calls and their responses.
If you deem that the user query has been fulfilled completely, which is at the top of each chain, you output "FINISHED" 
and after that a summary of the executed steps for the user. Be aware that your response is the only answer a user will 
receive, so always include relevant information to the user query in your response.
If a query requires searching, filtering, sorting and so on, the query is still only then fulfilled if the core intent 
of the query has been dealt with. For example, if a user wants to book a free desk, the query is only then fulfilled 
if a free desk was booked, not when a free desk was found or is available.
Further, if the user asks about multiple information or has multiple tasks to fulfill, the query is only then 
fulfilled if all information to all requested data has been tried to retrieve or if every single subtask has been 
successfully executed. For example, if a user requests the temperature from 6 different rooms, the chain needs to 
include calls to all of those 6 different rooms. Otherwise the query is still unfulfilled.
If a user query is still unfulfilled, you output "CONTINUE". Be aware that some user queries require a lot of API calls.
In that case you should still check if the whole query was fulfilled. Do not worry if you think the query is running 
indefinitely. Sometimes a query needs to call the same API call with different parameters multiple times. 
A query can also be unfulfilled if partial results have been received, but the overall user query is still missing 
more steps. For example, if a user requested to open an unidentified shelf, after finding that shelf id, the shelf 
still needs to be open.
If the query involves comparing results from different API calls and you determine that all necessary calls were made, 
you should output "FINISHED" as well followed with the result of such a comparison in natural language for the user."""

EVAL_PROMPT_SLIM = """
You are evaluating user queries against an API call hierarchy. Your task is to determine if the user query has been 
fulfilled completely in the call hierarchy. If it has been fulfilled, you output "FINISHED" and after that a summary 
of the executed steps and achieved result to the user. If it has not been fulfilled, you output "CONTINUE".
If the query involves comparing results from different API calls and you determine that all necessary calls were made,
you should output "FINISHED" as well followed with the result of such a comparison in natural language for the user.
The user will not receive any information except yours, so make sure to include all relevant information.
"""


class Evaluator(LLMAgent):
    llm: BaseChatModel
    planner_prompt: str

    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name='Evaluator',
            llm=llm.bind(stop=self._stop),
            system_prompt=EVAL_PROMPT
        )

    @property
    def _stop(self):
        return "API response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Plan step {}: "

    def _construct_scratchpad(
            self, history: List[Tuple[str, str]]
    ) -> str:
        if len(history) == 0:
            return ""
        scratchpad = ""
        for i, (plan, execution_res) in enumerate(history):
            scratchpad += f'Plan step {i + 1}: ' + plan + "\n"
            scratchpad += self._stop + execution_res + "\n"
        return scratchpad

    async def ainvoke(self, inputs: Dict[str, Any]) -> AgentMessage:

        self.system_prompt = EVAL_PROMPT_SLIM if inputs['config']['slim_prompts']['evaluator'] else EVAL_PROMPT
        self.examples = examples if inputs['config']['examples']['evaluator'] else []
        self.input_variables = ['input']
        self.message_template = "{input}"

        return await super().ainvoke({"input": inputs["input"], "history": inputs["history"]}, inputs["websocket"])
