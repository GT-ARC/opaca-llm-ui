from typing import Dict, List, Optional

import jsonref
from colorama import Fore
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, AIMessagePromptTemplate, \
    FewShotChatMessagePromptTemplate, MessagesPlaceholder


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

    def llama_str(self, agentName: bool = False):
        return (f'{{"name": "{(self.agent_name + "--" + self.action_name) if agentName else self.action_name}", '
                f'"description": {self.description}, "parameters": {self.params_in}, '
                f'"custom types": {self.custom_params}}}')


def add_dicts(d1: dict, d2: dict) -> dict:
    result = {}
    for key in d1.keys() | d2.keys():
        if isinstance(d1[key], dict) and isinstance(d2[key], dict):
            result[key] = add_dicts(d1[key], d2[key])
        else:
            result[key] = d1.get(key, 0) + d2.get(key, 0)
    return result


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


def openapi_to_llama(openapi_spec, use_agent_names: bool = False):
    functions = []
    error_msg = ""

    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            # 1. Resolve JSON references.
            try:
                spec = jsonref.replace_refs(spec_with_ref)
            except Exception as e:
                error_msg += f'Error while replacing references for unknown action. Cause: {str(e)}\n'
                continue

            # 2. Extract a name for the functions
            try:
                # The operation id is formatted as 'containerId-agentName-actionName'
                container_id, agent_name, function_name = spec.get("operationId").split(';')
            except Exception as e:
                error_msg += (f'Error while splitting the operation id: ({spec.get("operationId", "")}). '
                              f'Cause: {str(e)}\n')
                continue

            # 3. Extract a description and parameters.
            try:
                # OpenAI only allows up to 1024 characters in the description field
                desc = spec.get("description", "")[:1024] or spec.get("summary", "")[:1024]
            except Exception as e:
                error_msg += (f'Error while getting description for operation ({agent_name}--{function_name}). '
                              f'Cause: {str(e)}\n')
                continue

            req_body = (
                spec.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )

            required_params = req_body.get("required", [])
            params = {}
            for key, value in req_body.get("properties", {}).items():
                params[key] = {
                    "param_type": value.get("type"),
                    "required": True if key in required_params else False
                }

            functions.append(
                {
                    "name": agent_name + '--' + function_name if use_agent_names else function_name,
                    "description": desc,
                    "parameters": params
                }
            )

    return functions, error_msg


def openapi_to_functions(openapi_spec, use_agent_names: bool = False):
    functions = []
    error_msg = ""

    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            # 1. Resolve JSON references.
            try:
                spec = jsonref.replace_refs(spec_with_ref)
            except Exception as e:
                error_msg += f'Error while replacing references for unknown action. Cause: {str(e)}\n'
                continue

            # 2. Extract a name for the functions
            try:
                # The operation id is formatted as 'containerId-agentName-actionName'
                container_id, agent_name, function_name = spec.get("operationId").split(';')
            except Exception as e:
                error_msg += (f'Error while splitting the operation id: ({spec.get("operationId", "")}). '
                              f'Cause: {str(e)}\n')
                continue

            # 3. Extract a description and parameters.
            try:
                # OpenAI only allows up to 1024 characters in the description field
                desc = spec.get("description", "")[:1024] or spec.get("summary", "")[:1024]
            except Exception as e:
                error_msg += (f'Error while getting description for operation ({agent_name}--{function_name}). '
                              f'Cause: {str(e)}\n')
                continue

            schema = {"type": "object", "properties": {}}

            req_body = (
                spec.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            if req_body:
                schema["properties"]["requestBody"] = req_body

            params = spec.get("parameters", [])
            if params:
                param_properties = {
                    param["name"]: param["schema"]
                    for param in params
                    if "schema" in param
                }
                schema["properties"]["parameters"] = {
                    "type": "object",
                    "properties": param_properties,
                }

            functions.append(
                {
                    "type": "function",
                    "function": {
                        "name": agent_name + '--' + function_name if use_agent_names else function_name,
                        "description": desc,
                        "parameters": schema
                    }
                }
            )

    return functions, error_msg


def message_to_dict(msg):
    """
    Convert from Langchain classes (HumanMessage, AIMessage, SystemMessage) to JSON format used in the APIs
    """
    role = {
        HumanMessage: "user",
        AIMessage: "assistant",
        SystemMessage: "system",
    }[type(msg)]
    return {"role": role, "content": msg.content}


def message_to_class(msg):
    """
    Convert from JSON format used in the APIs to Langchain classes (HumanMessage, AIMessage, SystemMessage)
    """
    MessageType = {
        "user": HumanMessage,
        "assistant": AIMessage,
        "system": SystemMessage,
    }[msg["role"]]
    return MessageType(msg.get("content", ""))


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
