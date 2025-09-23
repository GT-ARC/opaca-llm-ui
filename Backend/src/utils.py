import os
import logging
from typing import Dict, List, Optional, Any

import jsonref
from fastapi import HTTPException

from .models import ConfigParameter, OpacaException, QueryResponse


logger = logging.getLogger(__name__)

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


def get_supported_models():
    return [
        (url, key, models.split(","))
        for url, key, models in zip(
            os.getenv("LLM_URLS", "openai").split(";"), 
            os.getenv("LLM_APIKEYS", "").split(";"), 
            os.getenv("LLM_MODELS", "gpt-4o-mini,gpt-4o").split(";"),
        )
    ]


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


def openapi_to_functions(openapi_spec, agent: str | None = None, strict: bool = False):
    functions = []
    error_msg = ""

    for path, methods in openapi_spec.get("paths", {}).items():
        for method, spec_with_ref in methods.items():
            # Resolve JSON references.
            try:
                spec = jsonref.replace_refs(spec_with_ref)
            except Exception as e:
                error_msg += f'Error while replacing references for unknown action. Cause: {e}\n'
                continue

            # Extract a name for the functions
            try:
                # The operation id is formatted as 'containerId-agentName-actionName'
                container_id, agent_name, function_name = spec.get("operationId").split(';')
                # action relevant for selected agent?
                if agent and agent_name != agent:
                    continue
            except Exception as e:
                error_msg += f'Error while splitting the operation id {spec.get("operationId")}. Cause: {e}\n'
                continue

            # Extract a description and parameters.
            desc = spec.get("description", "")[:1024] or spec.get("summary", "")[:1024]

            # assemble function block
            # structure of schema: type (str), required (list), properties (the actual parameters), additionalProperties (bool)
            schema = (spec.get("requestBody", {})
                        .get("content", {})
                        .get("application/json", {})
                        .get("schema"))
            schema.setdefault("properties", {})  # must be present even if no params
            if strict:
                schema["additionalProperties"] = False
                schema["required"] = list(schema["properties"])

            functions.append(
                {
                    "type": "function",
                    "name": agent_name + '--' + function_name,
                    "description": desc,
                    "parameters": schema,
                }
            )

    return functions, error_msg


def enforce_strictness(schema):
    if isinstance(schema, dict):
        schema.pop("format", None)  # optional: clean out OpenAPI stuff
        if schema.get("type") == "object":
            props = schema.get("properties", {})
            schema["required"] = list(props.keys())
            schema["additionalProperties"] = False  # ensure strict mode
            for prop_schema in props.values():
                enforce_strictness(prop_schema)
        elif schema.get("type") == "array":
            items = schema.get("items")
            if items:
                enforce_strictness(items)
        else:
            for v in schema.values():
                enforce_strictness(v)
    elif isinstance(schema, list):
        for item in schema:
            enforce_strictness(item)


def validate_config_input(values: Dict[str, Any], schema: Dict[str, ConfigParameter]):
    """
    Validates the given input values against the Configuration Schema
    :param values: The input dict of configuration parameters that was sent by the UI
    :param schema: The schema of the selected backend that the parameters should affect
    :return: Returns true if everything was successfully validated, false otherwise
    """

    # Check if all required parameters have been provided
    if not all(key in values.keys() for key in schema.keys() if schema[key].required):
        raise HTTPException(400, f'There are required configuration parameters missing!\n'
                                 f'Expected: {[key for key in schema.keys() if schema[key].required]}\n'
                                 f'Received: {[key for key in values.keys()]}')

    for key, value in values.items():
        # Check if key exist in schema
        if key not in schema.keys():
            raise HTTPException(400, f'No option named "{key}" was found!')

        # Make config parameter a dict for easier checks of optional fields
        if isinstance(schema[key], ConfigParameter):
            config_param = schema[key].model_dump()
        else:
            config_param = schema[key]

        # Validate type consistency
        if (config_param["type"] == "number" and not isinstance(value, (float, int))) or \
            (config_param["type"] == "integer" and not isinstance(value, int)) or \
            (config_param["type"] == "string" and not isinstance(value, str)) or \
            (config_param["type"] == "boolean" and not isinstance(value, bool)):
            raise HTTPException(400, f'Parameter "{key}" does not match the expected type "{config_param["type"]}"')
        elif config_param["type"] == "null" and value is not None:
            raise HTTPException(400, f'Parameter "{key}" does not match the expected type "{config_param["type"]}"')

        # Validate min/max limit
        if config_param["type"] in ["number", "integer"]:
            if config_param.get("minimum", None) is not None and value < config_param.get("minimum"):
                raise HTTPException(400, f'Parameter "{key}" cannot be smaller than its allowed minimum ({config_param["minimum"]})')
            if config_param.get("maximum", None) is not None and value > config_param.get("maximum"):
                raise HTTPException(400, f'Parameter "{key}" cannot be larger than its allowed maximum ({config_param["maximum"]})')

        # Validate enum
        if config_param.get("enum", None) and value not in schema[key].enum and not schema[key].free_input:
            raise HTTPException(400,f'Parameter "{key}" has to be one of "{schema[key].enum}"')


def transform_schema(schema):
    """Transform a JSON schema to meet OpenAI's requirements.

    This function:
    1. Resolves $ref references from $defs
    2. Adds additionalProperties: False to all object types
    3. Removes unnecessary fields like title and default
    4. Flattens and simplifies the schema structure
    5. Adds required name field for OpenAI compatibility
    """
    # Extract $defs if present
    defs = schema.get('$defs', {})

    def resolve_ref(ref):
        """Resolve a $ref reference by getting the schema from $defs"""
        if not ref.startswith('#/$defs/'):
            return None
        def_name = ref.split('/')[-1]
        return defs.get(def_name, {})

    def clean_schema(s):
        """Remove unnecessary fields and add additionalProperties: False to objects"""
        if not isinstance(s, dict):
            return s

        # Start with a new dict to only keep what we want
        cleaned = {}

        # Copy essential fields
        if 'type' in s:
            cleaned['type'] = s['type']
        if 'description' in s:
            cleaned['description'] = s['description']
        if 'properties' in s:
            cleaned['properties'] = {
                k: clean_schema(v) for k, v in s['properties'].items()
            }
        if 'items' in s:
            cleaned['items'] = clean_schema(s['items'])
        if 'required' in s:
            cleaned['required'] = s['required']
        if 'enum' in s:
            cleaned['enum'] = s['enum']

        # Add additionalProperties: False to objects
        if s.get('type') == 'object':
            cleaned['additionalProperties'] = False

        # Handle anyOf/allOf/oneOf
        for field in ['anyOf', 'allOf', 'oneOf']:
            if field in s:
                cleaned[field] = [clean_schema(item) for item in s[field]]

        return cleaned

    def process_schema(s):
        """Process schema by resolving refs and cleaning"""
        if not isinstance(s, dict):
            return s

        # Create a new dict to store processed schema
        processed = {}

        # Handle $ref first
        if '$ref' in s:
            ref_schema = resolve_ref(s['$ref'])
            if ref_schema:
                # Merge the resolved schema with any additional properties
                processed = process_schema(ref_schema)
                # Add any additional fields from the original schema
                for k, v in s.items():
                    if k != '$ref':
                        processed[k] = process_schema(v)
                return processed

        # Process each field
        for k, v in s.items():
            if k == '$defs':
                continue  # Skip $defs as we handle them separately
            elif isinstance(v, dict):
                processed[k] = process_schema(v)
            elif isinstance(v, list):
                processed[k] = [process_schema(item) for item in v]
            else:
                processed[k] = v

        return processed

    # Process the main schema
    processed_schema = process_schema(schema)

    # Clean the processed schema
    cleaned_schema = clean_schema(processed_schema)

    # Create the final schema with the required name field
    final_schema = {
        "format": {
            "type": "json_schema",
            "strict": True,
            "name": schema.get("title", "json_response"),  # Use title if available, otherwise default
            "schema": cleaned_schema
        }
    }

    return final_schema


def exception_to_result(user_query: str, exception: Exception) -> QueryResponse:
    """Convert an exception (generic or OpacaException) to a QueryResponse to be
    returned to the Chat-UI."""
    if isinstance(exception, OpacaException):
        return QueryResponse(query=user_query, content=exception.user_message, error=exception.error_message)
    else:
        return QueryResponse(query=user_query, content='Generation failed', error=str(exception))
