import json
import logging
from typing import Dict, List, Optional, Tuple
import time
import re
import requests

from langchain.chains.base import Chain
from langchain_community.utilities import RequestsWrapper
from langchain.prompts.prompt import PromptTemplate

from .utils import fix_json_error, OpacaLLM

logger = logging.getLogger(__name__)

examples = [
    {"input": """
API Call: http://localhost:8000/invoke/GetTemperature
Parameter: {"room": "1"}
Result: 23""", "output": "The temperature for room 1 is 23 degrees."},
    {"input": """
API Call: http://localhost:8000/invoke/IsFree
Parameter: {"desk": 4}
Result: False""", "output": """The desk 4 is currently not free."""},
    {"input": """
API Call: http://localhost:8000/invoke/GetShelfs
Parameter: {}
Result: [0, 1, 2, 3]""", "output": """The available desks are (0, 1, 2, 3)"""},
    {"input": """
API Call: http://localhost:8000/invoke/NavigateTo
Parameter: {"room": "Kitchen"}
Result: Turn left, move to the end of the hallway, then enter the door on your right.""", "output": """
To navigate to the kitchen, you have to turn left, move to the end of the hallway, then enter the door on your right."""},
]

CALLER_PROMPT_ALT = """You are an agent that generates answers to API calls.
You will be provided with an API call, which will include the endpoint that got called, the parameters that were used for that API call, and finally the result that was returned after calling that API.
Your task will be to generate in a chat-like the response for a user.
If there was an error or the api call was unsuccessful, then also generate an appropriate output to inform the user about the error."""


class Caller(Chain):
    llm: OpacaLLM
    action_spec: List
    requests_wrapper: RequestsWrapper
    max_iterations: Optional[int] = 15
    max_execution_time: Optional[float] = None
    early_stopping_method: str = "force"
    simple_parser: bool = False
    with_response: bool = False
    output_key: str = "result"
    request_headers: Dict = None

    def __init__(self, llm: OpacaLLM, action_spec: List, requests_wrapper: RequestsWrapper,
                 simple_parser: bool = False, with_response: bool = False, request_headers: Dict = None) -> None:
        super().__init__(llm=llm, action_spec=action_spec, requests_wrapper=requests_wrapper,
                         simple_parser=simple_parser, with_response=with_response, request_headers=request_headers)

    @property
    def _chain_type(self) -> str:
        return "Opaca LLM Caller"

    @property
    def input_keys(self) -> List[str]:
        return ["api_plan"]

    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]

    def _should_continue(self, iterations: int, time_elapsed: float) -> bool:
        if self.max_iterations is not None and iterations >= self.max_iterations:
            return False
        if (
                self.max_execution_time is not None
                and time_elapsed >= self.max_execution_time
        ):
            return False

        return True

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Response: "

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the llm call with."""
        return "Thought: "

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

    def _get_action_and_input(self, llm_output: str) -> Tuple[str, str]:
        if "Execution Result:" in llm_output:
            return "Execution Result", llm_output.split("Execution Result:")[-1].strip()
        # \s matches against tab/newline/whitespace
        regex = r"Operation:[\s]*(.*?)[\n]*Input:[\s]*(.*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            # TODO: not match, just return
            raise ValueError(f"Could not parse LLM output: `{llm_output}`")
        action = match.group(1).strip()
        action_input = match.group(2)
        if action not in ["GET", "POST", "DELETE", "PUT"]:
            raise NotImplementedError

        # avoid error in the JSON format
        action_input = fix_json_error(action_input)

        return action, action_input

    def _get_response(self, action: str, action_input: str) -> str:
        action_input = action_input.strip().strip('`')
        left_bracket = action_input.find('{')
        right_bracket = action_input.rfind('}')
        action_input = action_input[left_bracket:right_bracket + 1]
        try:
            data = json.loads(action_input)
        except json.JSONDecodeError as e:
            raise e

        desc = data.get("description", "No description")
        query = data.get("output_instructions", None)

        params, request_body = None, None
        if action == "GET":
            if 'params' in data:
                params = data.get("params")
                response = self.requests_wrapper.get(data.get("url"), params=params)
            else:
                response = self.requests_wrapper.get(data.get("url"))
        elif action == "POST":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.post(data["url"], params=params, data=request_body)
        elif action == "PUT":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.put(data["url"], params=params, data=request_body)
        elif action == "DELETE":
            params = data.get("params")
            request_body = data.get("data")
            response = self.requests_wrapper.delete(data["url"], params=params, json=request_body)
        else:
            raise NotImplementedError

        if isinstance(response, requests.models.Response):
            if response.status_code != 200:
                return response.text
            response_text = response.text
        elif isinstance(response, str):
            response_text = response
        else:
            raise NotImplementedError

        return response_text, params, request_body, desc, query

    def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()
        intermediate_steps: List[Tuple[str, str]] = []

        api_plan = inputs['api_plan']
        api_call, params = api_plan.split(';')
        logger.info(f'Caller: Attempting to call http://localhost:8000/invoke/{api_call} with parameters: {params}')

        response = requests.post("http://localhost:8000/invoke/" + api_call, json=json.loads(params), headers=self.request_headers)

        logger.info(f'Caller: Received response: {response.text}')

        messages = [{"role": "system", "content": CALLER_PROMPT_ALT}]
        for example in examples:
            messages.append({"role": "human", "content": example["input"]})
            messages.append({"role": "ai", "content": example["output"]})
        messages.append({"role": "human", "content": f"API Call: {api_call}\nParameter: {params}\nResult: {response.text}"})

        caller_output = self.llm.call(messages)

        return {'result': caller_output}

        """
        api_url = self.action_spec.servers[0]['url']
        matched_endpoints = get_matched_endpoint(self.action_spec, api_plan)
        endpoint_docs_by_name = {name: docs for name, _, docs in self.api_spec.endpoints}
        api_doc_for_caller = ""
        assert len(matched_endpoints) == 1, f"Found {len(matched_endpoints)} matched endpoints, but expected 1."
        endpoint_name = matched_endpoints[0]
        tmp_docs = deepcopy(endpoint_docs_by_name.get(endpoint_name))
        if 'responses' in tmp_docs and 'content' in tmp_docs['responses']:
            if 'application/json' in tmp_docs['responses']['content']:
                tmp_docs['responses'] = tmp_docs['responses']['content']['application/json']['schema']['properties']
            elif 'application/json; charset=utf-8' in tmp_docs['responses']['content']:
                tmp_docs['responses'] = tmp_docs['responses']['content']['application/json; charset=utf-8']['schema'][
                    'properties']
        if not self.with_response and 'responses' in tmp_docs:
            tmp_docs.pop("responses")
        tmp_docs = yaml.dump(tmp_docs)
        encoder = tiktoken.encoding_for_model('text-davinci-003')
        encoded_docs = encoder.encode(tmp_docs)
        if len(encoded_docs) > 1500:
            tmp_docs = encoder.decode(encoded_docs[:1500])
        api_doc_for_caller += f"== Docs for {endpoint_name} == \n{tmp_docs}\n"

        caller_prompt = PromptTemplate(
            template=CALLER_PROMPT,
            partial_variables={
                "api_url": api_url,
                "api_docs": api_doc_for_caller,
            },
            input_variables=["api_plan", "background", "agent_scratchpad"],
        )

        caller_chain = LLMChain(llm=self.llm, prompt=caller_prompt)

        while self._should_continue(iterations, time_elapsed):
            scratchpad = self._construct_scratchpad(intermediate_steps)
            caller_chain_output = caller_chain.run(api_plan=api_plan, background=inputs['background'],
                                                   agent_scratchpad=scratchpad, stop=self._stop)
            logger.info(f"Caller: {caller_chain_output}")

            action, action_input = self._get_action_and_input(caller_chain_output)
            if action == "Execution Result":
                return {"result": action_input}
            response, params, request_body, desc, query = self._get_response(action, action_input)

            called_endpoint_name = action + ' ' + json.loads(action_input)['url'].replace(api_url, '')
            called_endpoint_name = get_matched_endpoint(self.api_spec, called_endpoint_name)[0]
            api_path = api_url + called_endpoint_name.split(' ')[-1]
            api_doc_for_parser = endpoint_docs_by_name.get(called_endpoint_name)
            if self.scenario == 'spotify' and endpoint_name == "GET /search":
                if params is not None and 'type' in params:
                    search_type = params['type'] + 's'
                else:
                    params_in_url = json.loads(action_input)['url'].split('&')
                    for param in params_in_url:
                        if 'type=' in param:
                            search_type = param.split('=')[-1] + 's'
                            break
                api_doc_for_parser['responses']['content']['application/json']["schema"]['properties'] = {
                    search_type: api_doc_for_parser['responses']['content']['application/json']["schema"]['properties'][
                        search_type]}

            if not self.simple_parser:
                response_parser = ResponseParser(
                    llm=self.llm,
                    api_path=api_path,
                    api_doc=api_doc_for_parser,
                )
            else:
                response_parser = SimpleResponseParser(
                    llm=self.llm,
                    api_path=api_path,
                    api_doc=api_doc_for_parser,
                )

            params_or_data = {
                "params": params if params is not None else "No parameters",
                "data": request_body if request_body is not None else "No request body",
            }
            parsing_res = response_parser.run(query=query, response_description=desc, api_param=params_or_data,
                                              json=response)
            logger.info(f"Parser: {parsing_res}")

            intermediate_steps.append((caller_chain_output, parsing_res))

            iterations += 1
            time_elapsed = time.time() - start_time

        return {"result": caller_chain_output}
        """
