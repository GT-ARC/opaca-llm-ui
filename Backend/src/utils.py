import logging
from typing import Dict, Any


from .models import ConfigParameter


logger = logging.getLogger(__name__)



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

