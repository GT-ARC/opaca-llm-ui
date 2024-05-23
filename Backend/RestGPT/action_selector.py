from typing import Any, Dict, List, Optional, Tuple
import re
import logging

from langchain.chains.base import Chain
from langchain.chains.llm import LLMChain
from langchain.prompts.base import BasePromptTemplate
from langchain.prompts.prompt import PromptTemplate

from .utils import ReducedOpenAPISpec, get_matched_action, OpacaLLM

logger = logging.getLogger()

icl_examples = {
    "opaca": """Example 1:
Background: No background.
User query: Get the temperature of the room with id 2
Action call 1: GetTemperature;{{"room": "2"}}
Action response: The temperature in the room with id 2 is 23 degrees.

Example 2:
Background: No background.
User query: Book the desk with id 5
Action call 2: BookDesk;{{"desk": 5}}
Action response: Successfully booked the desk with id 5.

Example 3:
Background: No background.
User query: Check if the desk with id 3 is free
Action call 2: IsFree;{{"desk": 3}}
Action response: The desk with id 0 is free.

Example 4:
Background: No background.
User Query: Check if the shelf with id 1 contains plates.
Action call 1: GetContents;{{"shelf": 1}}
Action response: The shelf with id 1 contains plates.
""",

    "tmdb": """Example 1:

Background: The id of Wong Kar-Wai is 12453
User query: give me the latest movie directed by Wong Kar-Wai.
API calling 1: GET /person/12453/movie_credits to get the latest movie directed by Wong Kar-Wai (id 12453)
API response: The latest movie directed by Wong Kar-Wai is The Grandmaster (id 44865), ...

Example 2:

Background: No background
User query: search for movies produced by DreamWorks Animation
API calling 1: GET /search/company to get the id of DreamWorks Animation
API response: DreamWorks Animation's company_id is 521
Instruction: Continue. Search for the movies produced by DreamWorks Animation
API calling 2: GET /discover/movie to get the movies produced by DreamWorks Animation
API response: Puss in Boots: The Last Wish (id 315162), Shrek (id 808), The Bad Guys (id 629542), ...

Example 3:

Background: The id of the movie Happy Together is 18329
User query: search for the director of Happy Together
API calling 1: GET /movie/18329/credits to get the director for the movie Happy Together
API response: The director of Happy Together is Wong Kar-Wai (12453)

Example 4:

Background: No background
User query: search for the highest rated movie directed by Wong Kar-Wai
API calling 1: GET /search/person to search for Wong Kar-Wai
API response: The id of Wong Kar-Wai is 12453
Instruction: Continue. Search for the highest rated movie directed by Wong Kar-Wai (id 12453)
API calling 2: GET /person/12453/movie_credits to get the highest rated movie directed by Wong Kar-Wai (id 12453)
API response: The highest rated movie directed by Wong Kar-Wai is In the Mood for Love (id 843), ...
""",
    "spotify": """Example 1:
Background: No background
User query: what is the id of album Kind of Blue.
API calling 1: GET /search to search for the album "Kind of Blue"
API response: Kind of Blue's album_id is 1weenld61qoidwYuZ1GESA

Example 2:
Background: No background
User query: get the newest album of Lana Del Rey (id 00FQb4jTyendYWaN8pK0wa).
API calling 1: GET /artists/00FQb4jTyendYWaN8pK0wa/albums to get the newest album of Lana Del Rey (id 00FQb4jTyendYWaN8pK0wa)
API response: The newest album of Lana Del Rey is Did you know that there's a tunnel under Ocean Blvd (id 5HOHne1wzItQlIYmLXLYfZ), ...

Example 3:
Background: The ids and names of the tracks of the album 1JnjcAIKQ9TSJFVFierTB8 are Yellow (3AJwUDP919kvQ9QcozQPxg), Viva La Vida (1mea3bSkSGXuIRvnydlB5b)
User query: append the first song of the newest album 1JnjcAIKQ9TSJFVFierTB8 of Coldplay (id 4gzpq5DPGxSnKTe4SA8HAU) to my player queue.
API calling 1: POST /me/player/queue to add Yellow (3AJwUDP919kvQ9QcozQPxg) to the player queue
API response: Yellow is added to the player queue
"""
}

ACTION_SELECTOR_PROMPT_ALT = """
You are a planner that plans a sequence of RESTful API calls to assist with user queries against an API. 
You will receive a list of known services. These services will include actions. Only use the exact action names from this list. 
Create a valid HTTP request which would succeed when called. Your http requests will always be of the type POST. 
If an action requires further parameters, use the most fitting parameters from the user request. 
If an action requires a parameter but there were no suitable parameters in the user request, generate a fitting value 
for the missing required parameter field. For example, if you notice from the action list that the required parameter
"room" was not given in the user query, try to guess a valid value for this parameter based on its type.
If an action does not require parameters, just output an empty json array like {{}}.
If you think there were no fitting parameters in the user request, just create imaginary values for them based on their names. 
Do not use actions or parameters that are not included in the list. If there are no fitting actions in the list, 
include within your response the absence of such an action. If the list is empty, include in your response that there 
are no available services at all. If you think there is a fitting action, then your answer should only include the API 
call and the required parameters of that call, which will be included in a json style format after the request url. 
Your answer should only include the request url and the parameters in a JSON format, nothing else. Here is the format in which you should answer:

http://localhost:8000/invoke/{{action_name}};{{\"parameter_name\": \"value\"}}

You have to replace {{action_name}} with the exact name of the most fitting action from the following list:

{actions}

An example would look as follows:
User query: What is the current noise level in the room with id 1?
API Call 1: http://localhost:8000/invoke/GetNoise;{{\"room\": \"1\"}}
API Response: The noise in the room with id 1 is 60 decibel.

Another example without a fitting parameter in the user request could look like follows:
User query: What is the current humidity?
API Call 1: http://localhost:8000/invoke/GetHumidity;{{\"room\": \"0\"}}
API Response: The humidity in the room with id 0 is 40 percent.

Begin!

User query: {plan}
"""

# Thought: I am finished executing the plan and have the information the user asked for or the data the used asked to create
# Final Answer: the final output from executing the plan. If the user's query contains filter conditions, you need to filter the results as well. For example, if the user query is "Search for the first person whose name is 'Tom Hanks'", you should filter the results and only output the first person whose name is 'Tom Hanks'.
ACTION_SELECTOR_PROMPT = """You are an agent that plans action calls to assist with user queries.
You should always give your action plans in the following format: "action_name;parameters". 
You will be provided a list of action names and their parameters. Use only action names and parameter keys that are found within this list.
In this list, the parameters concerning an action will immediately follow the name of the action. Use only parameter key names for an action that are also associated with that action.
As a value for a parameter, use direct information provided in the user request. For example, if a user wants to know what the temperature in the room with id 1 is, use "1" as the value for the parameter "room".
If you think a parameter value is missing in the user request but is required for the correct action call, output "Missing Parameter Value for {{parameter_key}}" where {{parameter_key}} is the required parameter without a value.

Here is the list of action names and parameters.
Only use action names or parameters in your response that are listed here.

{actions}

Starting below, you should always follow this format:

User query: The query a user wants help with related to the list of actions.
Action call 1: The first action call you want to make. Note the action call can contain conditions such as filtering, sorting, etc. For example, "GetDesks;{{}}" to get all available desk id's, or "IsFree;{{"desk": 0}}" to check if the desk with id 0 is free and available to book. If the user query contains some filter condition, such as the if a desk is free, a free desk in the coldest room, a free desk in the room with the least amount of noise, then the action calling plan should also contain the filter condition. If you think there is no need to call an action, output "No action call needed." and then output the final answer according to the user query.
Action response: The response of Action call 1.
Instruction: Another model will evaluate whether the user query has been fulfilled. If the instruction contains "continue", then you should make another action call following this instruction.
... (this Action call n and Action response can repeat N times, but most queries can be solved in 1-3 step).

{icl_examples}

Begin!

Background: {background}
User query: {plan}
Action call 1: {agent_scratchpad}"""


class ActionSelector(Chain):
    llm: OpacaLLM
    action_spec: List
    action_selector_prompt: str
    output_key: str = "result"

    def __init__(self, llm: OpacaLLM, action_spec: List, action_selector_prompt=ACTION_SELECTOR_PROMPT_ALT) -> None:
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
        return "API Call {}: "

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
        # inputs: background, plan, (optional) history, instruction
        #if 'history' in inputs:
        #    scratchpad = self._construct_scratchpad(inputs['history'], inputs['instruction'])
        #else:
        #    scratchpad = ""
        scratchpad = ""
        action_desc = [f'name: {action.name}, parameters: {action.parameters}' for action in
                       self.action_spec]
        action_desc = '\n'.join(action_desc)
        action_selector_prompt = PromptTemplate(
            template=self.action_selector_prompt,
            partial_variables={"actions": action_desc},# "icl_examples": icl_examples['opaca']},
            input_variables=["plan", "background", "agent_scratchpad"],
        )
        #action_selector_chain = LLMChain(llm=self.llm, prompt=self.action_selector_prompt)
        action_selector_chain = action_selector_prompt | self.llm.bind(stop=self._stop)
        action_selector_chain_output = action_selector_chain.invoke(input={"plan": inputs['plan'], "background": inputs['background'],
                                                                           "agent_scratchpad": scratchpad})

        action_plan = re.sub(r"API Call \d+: ", "", action_selector_chain_output).strip()

        finish = re.match(r"No Action needed.(.*)", action_plan)
        if finish is not None:
            return {"result": action_plan}

        while get_matched_action(self.action_spec, action_plan) is None:
            logger.info(
                "API Selector: The action you called is not in the list of available action. Please use another action.")
            scratchpad += action_selector_chain_output + "\nThe action you called is not in the list of available actions. Please use another action.\n"
            action_selector_chain_output = action_selector_chain.invoke({"plan": inputs['plan'], "background": inputs['background'],
                                                                         "agent_scratchpad": scratchpad})
            action_plan = re.sub(r"API Call \d+: ", "", action_selector_chain_output).strip()
            logger.info(f"API Selector: {action_plan}")

        logger.info(f"API Selector: {action_plan}")

        return {"result": action_plan}
