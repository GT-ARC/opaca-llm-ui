import logging
from typing import Dict, Any

import jsonref

from .models import ConfigParameter


logger = logging.getLogger(__name__)


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
    :param schema: The schema of the selected prompting method that the parameters should affect
    :return: Returns true if everything was successfully validated, false otherwise
    """

    # Check if all required parameters have been provided
    if not all(key in values.keys() for key in schema.keys() if schema[key].required):
        raise ValueError(f'There are required configuration parameters missing!\n'
                         f'Expected: {[key for key in schema.keys() if schema[key].required]}\n'
                         f'Received: {[key for key in values.keys()]}')

    for key, value in values.items():
        # Check if key exist in schema
        if key not in schema.keys():
            raise ValueError(f'No option named "{key}" was found!')

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
            raise TypeError(f"Parameter '{key}' does not match the expected type '{config_param['type']}'")
        elif config_param["type"] == "null" and value is not None:
            raise TypeError(f"Parameter '{key}' does not match the expected type '{config_param['type']}'")

        # Validate min/max limit
        if config_param["type"] in ["number", "integer"]:
            if config_param.get("minimum", None) is not None and value < config_param.get("minimum"):
                raise ValueError(f"Parameter '{key}' cannot be smaller than its allowed minimum ({config_param['minimum']})")
            if config_param.get("maximum", None) is not None and value > config_param.get("maximum"):
                raise ValueError(f"Parameter '{key}' cannot be larger than its allowed maximum ({config_param['maximum']})")

        # Validate enum
        if config_param.get("enum", None) and value not in schema[key].enum and not schema[key].free_input:
            raise ValueError(f"Parameter '{key}' has to be one of {schema[key].enum}")


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
