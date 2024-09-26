import jsonref
import requests
import re

from typing import Optional, List, Dict, Any, Union, Sequence, Tuple
from colorama import Fore
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnableConfig

LLAMA_URL = "http://10.0.64.101"


class ColorPrint:
    def __init__(self):
        self.color_mapping = {
            "Planner": Fore.RED,
            "API Selector": Fore.YELLOW,
            "Caller": Fore.BLUE,
            "Final Answer": Fore.GREEN,
            "Code": Fore.WHITE,
        }

    def write(self, data):
        module = data.split(':')[0]
        if module not in self.color_mapping:
            print(data, end="")
        else:
            print(self.color_mapping[module] + data + Fore.RESET, end="")


class Parameter:
    type: str
    required: bool

    def __init__(self, type_in: str, required: bool, items: Optional = None):
        self.type = type_in
        self.required = required
        self.items = items

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return (f'{{type: {self.type}, required: {self.required}'
                f'{", " + str(self.items) + "}" if self.items is not None else "}"}')

    class ArrayItems:
        type: str

        def __init__(self, type_in: str, items: Optional = None):
            self.type = type_in
            self.items = items

        def __repr__(self):
            return self.__str__()

        def __str__(self):
            return f'{{type: {self.type}{", " + str(self.items) + "}" if self.items is not None else "}"}'


class Action:

    action_name: str
    description: Optional[str]
    params_in: Optional[Dict]
    param_out: Optional[str]
    agent_name: str
    container_id: str
    custom_params: Optional[Dict]

    def __init__(self):
        self.action_name = ""
        self.description = ""
        self.params_in = {}
        self.param_out = ""
        self.agent_name = ""
        self.container_id = ""
        self.custom_params = {}

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return (f'{{{self.action_name};{self.description};{self.params_in};{self.param_out};{self.agent_name};'
                f'{self.container_id};{self.custom_params}}}')

    def planner_str(self, agentName: bool = False):
        return (f'{{Name: {(self.agent_name + "--" + self.action_name) if agentName else self.action_name}, '
                f'Description: {self.description}, Parameters: {self.params_in}}}')

    def selector_str(self, agentName: bool = False):
        return (f'{{Name: {(self.agent_name + "--" + self.action_name) if agentName else self.action_name}, '
                f'Description: {self.description}, Parameters: {self.params_in}, '
                f'Custom Types: {self.custom_params}}}')


def get_reduced_action_spec(action_spec: Dict) -> List:
    """
    Takes in the openapi specification of the available actions form the connected opaca platform.
    Results in a string in a list-like format.

    Output format:
    "[[action_name;description;[params_in];param_out;agent;container_id;[custom_params]], ...]"
    """
    action_spec = jsonref.replace_refs(action_spec)
    action_list = []
    action_paths = action_spec["paths"]
    for _, content in action_paths.items():
        action = Action()
        action.container_id, action.agent_name, action.action_name = content["post"]["operationId"].split(';')
        action.description = content["post"]["description"] if "description" in content["post"] else ""

        param_schema = content["post"]["requestBody"]["content"]["application/json"]["schema"]
        required = param_schema["required"] if "required" in param_schema.keys() else []
        if "properties" in param_schema:
            for p_name, p_type in content["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"].items():
                if "$ref" in p_type.keys():
                    p = resolve_reference(action_spec, p_type["$ref"])
                    p_required = p["required"] if "required" in p.keys() else []
                    p_parameters = {}
                    for name, p_content in p["properties"].items():
                        p_parameters[name] = Parameter(p_content["type"], True if name in p_required else False)
                    action.custom_params[p["title"]] = p_parameters
                is_type = p_type["type"] if "type" in p_type else p_type["$ref"].split("/")[-1]
                is_required = True if p_name in required else False
                action.params_in[p_name] = Parameter(is_type, is_required)
                if "type" in p_type and p_type["type"] == "array":
                    action.params_in[p_name].items = resolve_array_items(p_type)

        res_schema = content["post"]["responses"]["200"]["content"]["*/*"]["schema"]
        action.param_out = res_schema["type"] if "type" in res_schema.keys() else ""
        action_list.append(action)
    return action_list


def resolve_array_items(p_type: Dict) -> Parameter.ArrayItems:
    if p_type["items"]["type"] == "array":
        array_item = Parameter.ArrayItems("array")
        array_item.items = resolve_array_items(p_type["items"])
        return array_item
    else:
        return Parameter.ArrayItems(p_type["items"]["type"])


def resolve_reference(action_spec: Dict, ref: str) -> Dict:
    if ref[0] != '#':
        raise RuntimeError("Unknown reference in action spec")
    out = action_spec
    for component in ref[2:].split('/'):
        out = out[component]
    return out


class OpacaLLM(BaseChatModel):

    url: str = ""
    model: str = ""

    def __init__(self, url, model, **data: Any):
        super().__init__(**data)
        self.url = url
        self.model = model

    @property
    def _llm_type(self) -> str:
        return "Llama-3 Proxy"

    def invoke(
            self,
            input: Union[PromptValue, str, Sequence[Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]]],
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[List[str]] = None,
            **kwargs: Any
    ) -> str:
        return self._generate(format_llama3(input), stop)

    def _generate(
            self,
            prompt: Any,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any
    ) -> str:
        response = requests.post(
            f'{self.url}/api/chat',
            json={
                'messages': prompt,
                'model': self.model,
                'stream': False
            }
        ).json()

        output = response['message']['content']
        output = output.replace("\\n", "\n").replace('\\"', '"').strip()

        if stop is None:
            return output

        for word in stop:
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return output


def build_prompt(
        system_prompt: str,
        examples: List[Dict[str, str]],
        input_variables: List[str],
        message_template: str
    ) -> ChatPromptTemplate:

    example_prompt = ChatPromptTemplate.from_messages(
        [
            HumanMessagePromptTemplate.from_template("{input}"),
            AIMessagePromptTemplate.from_template("{output}")
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        input_variables=input_variables,
        example_prompt=example_prompt,
        examples=examples
    )

    final_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            few_shot_prompt,
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", message_template),
        ]
    )

    return final_prompt


def format_llama3(prompt_values: PromptValue):
    messages = []

    for message in prompt_values.messages:
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            raise ValueError(f'Unknown message type: {type(messages)}')

        content = message.content
        content = content.replace("\\n", "").replace('\\"', '"')
        content = fix_parentheses(content)

        messages.append({"role": role, "content": content})
    return messages


def fix_parentheses(x: str) -> str:
    # Prevents langchain from thinking there are parameters expected in the string
    return re.sub(r"\{", "{{", re.sub(r"}", "}}", x))
