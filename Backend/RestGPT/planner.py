import logging
from typing import Any, Dict, List, Optional, Tuple
import re

from langchain.chains.base import Chain
from langchain.chains import LLMChain
from langchain.prompts.prompt import PromptTemplate
from langchain.llms.base import BaseLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate

logger = logging.getLogger()

icl_examples = {
    "opaca": """Example 1:
User query: What is the current temperature in room 1?
Plan step 1: Get the temperature in room 1.
Action response: The temperature in room 1 is 23 degrees.
Thought I am finished executing a plan and have the information the user asked for or the data the user asked to create.
Final Answer: The temperature in room 1 is 23 degrees.

Example 2:
User query: Book me the desk with id 6.
Plan step 1: Check if the desk with id 6 is currently free.
Action response: The desk with id 6 is free.
Plan step 2: Book the desk with id 6.
Action response: Successfully booked the desk with id 6.
Thought: I am finished executing a plan and completed the user's instructions
Final Answer: The desk with id 6 was successfully booked for you.

Example 3:
User query: Please open the shelf with cups in it.
Plan step 1: Check if the shelf with id 0 contains cups.
Action response: The shelf with id 0 does not contain any cups.
Plan step 2: Check if the shelf with id 1 contains cups.
Action response: The shelf with id 1 does contain cups.
Plan step 3: Open the shelf with id 1.
Action response: Successfully opened the shelf with id 1.
Thought: I am finished executing a plan and completed the user's instructions'
Final Answer: The shelf with id 1 containing cups has been opened.
""",
    "tmdb": """Example 1:
User query: give me some movies performed by Tony Leung.
Plan step 1: search person with name "Tony Leung"
API response: Tony Leung's person_id is 1337
Plan step 2: collect the list of movies performed by Tony Leung whose person_id is 1337
API response: Shang-Chi and the Legend of the Ten Rings, In the Mood for Love, Hero
Thought: I am finished executing a plan and have the information the user asked for or the data the used asked to create
Final Answer: Tony Leung has performed in Shang-Chi and the Legend of the Ten Rings, In the Mood for Love, Hero

Example 2:
User query: Who wrote the screenplay for the most famous movie directed by Martin Scorsese?
Plan step 1: search for the most popular movie directed by Martin Scorsese
API response: Successfully called GET /search/person to search for the director "Martin Scorsese". The id of Martin Scorsese is 1032
Plan step 2: Continue. search for the most popular movie directed by Martin Scorsese (1032)
API response: Successfully called GET /person/{{person_id}}/movie_credits to get the most popular movie directed by Martin Scorsese. The most popular movie directed by Martin Scorsese is Shutter Island (11324)
Plan step 3: search for the screenwriter of Shutter Island
API response: The screenwriter of Shutter Island is Laeta Kalogridis (20294)
Thought: I am finished executing a plan and have the information the user asked for or the data the used asked to create
Final Answer: Laeta Kalogridis wrote the screenplay for the most famous movie directed by Martin Scorsese.
""",
    "spotify": """Example 1:
User query: set the volume to 20 and skip to the next track.
Plan step 1: set the volume to 20
API response: Successfully called PUT /me/player/volume to set the volume to 20.
Plan step 2: skip to the next track
API response: Successfully called POST /me/player/next to skip to the next track.
Thought: I am finished executing a plan and completed the user's instructions
Final Answer: I have set the volume to 20 and skipped to the next track.

Example 2:
User query: Make a new playlist called "Love Coldplay" containing the most popular songs by Coldplay
Plan step 1: search for the most popular songs by Coldplay
API response: Successfully called GET /search to search for the artist Coldplay. The id of Coldplay is 4gzpq5DPGxSnKTe4SA8HAU
Plan step 2: Continue. search for the most popular songs by Coldplay (4gzpq5DPGxSnKTe4SA8HAU)
API response: Successfully called GET /artists/4gzpq5DPGxSnKTe4SA8HAU/top-tracks to get the most popular songs by Coldplay. The most popular songs by Coldplay are Yellow (3AJwUDP919kvQ9QcozQPxg), Viva La Vida (1mea3bSkSGXuIRvnydlB5b).
Plan step 3: make a playlist called "Love Coldplay"
API response: Successfully called GET /me to get the user id. The user id is xxxxxxxxx.
Plan step 4: Continue. make a playlist called "Love Coldplay"
API response: Successfully called POST /users/xxxxxxxxx/playlists to make a playlist called "Love Coldplay". The playlist id is 7LjHVU3t3fcxj5aiPFEW4T.
Plan step 5: Add the most popular songs by Coldplay, Yellow (3AJwUDP919kvQ9QcozQPxg), Viva La Vida (1mea3bSkSGXuIRvnydlB5b), to playlist "Love Coldplay" (7LjHVU3t3fcxj5aiPFEW4T)
API response: Successfully called POST /playlists/7LjHVU3t3fcxj5aiPFEW4T/tracks to add Yellow (3AJwUDP919kvQ9QcozQPxg), Viva La Vida (1mea3bSkSGXuIRvnydlB5b) in playlist "Love Coldplay" (7LjHVU3t3fcxj5aiPFEW4T). The playlist id is 7LjHVU3t3fcxj5aiPFEW4T.
Thought: I am finished executing a plan and have the data the used asked to create
Final Answer: I have made a new playlist called "Love Coldplay" containing Yellow and Viva La Vida by Coldplay.
"""
}

PLANNER_PROMPT = """You are an agent that plans solution to user queries.
You should always give your plan in natural language.
Another model will receive your plan and find the right agent action calls and give you the result in natural language.
If you assess that the current plan has not been fulfilled, you can output "Continue" to let the action selector select another action to fulfill the plan.
If you think you have got the final answer or the user query has been fulfilled, just output the answer immediately. If the query has not been fulfilled, you should continue to output your plan.
In most case, search, filter, and sort should be completed in a single step.
The plan should be as specific as possible. It is better not to use pronouns in plan, but to use the corresponding results obtained previously. For example, instead of "Get the most popular movie directed by this person", you should output "Get the most popular movie directed by Martin Scorsese (1032)". If you want to iteratively query something about items in a list, then the list and the elements in the list should also appear in your plan.
The plan should be straightforward. If you want to search, sort or filter, you can put the condition in your plan. For example, if the query is "Open the shelf with the plates", instead of "get the list of items of all shelfs", you should output "get the list of items of the first shelf".

Starting below, you should always follow this format:

User query: The query a User wants help with related to the agent actions.\n
Plan step 1: The first step of your plan for how to solve the query.\n
Action response: The result of executing the first step of your plan, including the specific action call made.\n
Plan step 2: Based on the action response, the second step of your plan for how to solve the query.\n
Action response: The result of executing the second step of your plan.\n
... (this Plan step n and Action response can repeat N times)\n
Thought: I am finished executing a plan and have the information the user asked for or the data the user asked to create\n
Final Answer: The final output from executing the plan\n

{icl_examples}

Begin!

User query: {input}\n
Plan step 1: {agent_scratchpad}"""

PLANNER_PROMPT_ALT = """
You are a simple repeating agent. All user queries you will receive, you will repeat exactly once.\n
For example, if a user queries consists of "What is the weather today?", your response should be "What is the weather today?".\n 
Once you have repeated the user query, you stop and do not output any additional responses. Do not create additional queries that were not part of the original user query.\n

Starting below, you should always follow this format:

User query: The query a User wants help with.
Response: Your response which is just a copy of the user query.
Finished

Example 1:
User query: How are you?
Response: How are you?
Finished

Example 2:
User query: What is the weather?
Response: What is the weather?
Finished

Example 3:
User query: I want to go skiing
Response: I want to go skiing
Finished

Begin!

User query: {input}\n
Response:"""


class Planner(Chain):
    llm: BaseLLM
    planner_prompt: str
    output_key: str = "result"

    def __init__(self, llm: BaseLLM, planner_prompt=PLANNER_PROMPT) -> None:
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
        return "Action response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Plan step {}: "

    @property
    def _stop(self) -> List[str]:
        return [
            #f"Finished"
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
        # print("Scrachpad: \n", scratchpad)
        planner_prompt = PromptTemplate(
            template=self.planner_prompt,
            partial_variables={
                "agent_scratchpad": scratchpad,
                "icl_examples": icl_examples['opaca'],
            },
            input_variables=["input"]
        )
        planner_chain = planner_prompt | self.llm.bind(stop=self._stop)
        # planner_chain = LLMChain(llm=self.llm, prompt=planner_prompt)
        logger.info(f'QUERY: {inputs}')
        planner_chain_output = planner_chain.invoke(input=inputs['input'])#, stop=self._stop)

        #planner_chain_output = re.sub(r"Plan step \d+: ", "", planner_chain_output).strip()
        planner_chain_output = re.sub(r"Finished", "", planner_chain_output).strip()

        return {"result": planner_chain_output}
