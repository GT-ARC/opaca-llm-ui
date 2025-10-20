import logging


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
