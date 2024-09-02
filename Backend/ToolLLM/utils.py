from typing import List, Dict

import jsonref

from Backend.RestGPT import Parameter


def openapi_to_functions(openapi_spec):
    functions = []

    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            # 1. Resolve JSON references.
            spec = jsonref.replace_refs(spec_with_ref)

            # 2. Extract a name for the functions.
            function_name = spec.get("operationId").split(';')[2]

            # 3. Extract a description and parameters.
            desc = spec.get("description") or spec.get("summary", "")

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
                {"type": "function", "function": {"name": function_name, "description": desc, "parameters": schema}}
            )

    return functions


def transform_to_openai_tools(action_list: List) -> List:
    actions_out = []
    for action in action_list:
        properties = {}

        # Loop through the parameters in action.params_in
        for key, val in action.params_in.items():
            properties[key] = get_param_format(val)

        for c_name, c_val in action.custom_params.items():
            # This uses 'lower()' because parameter names are normally lower case but the
            # custom parameters are typically upper case but a replacement needs to occur
            properties[c_name.lower()] = {
                'type': 'object',
                'properties': {key: get_param_format(val) for key, val in c_val.items()},
                'required': [key for key, val in c_val.items() if val.required]
            }

        actions_out.append({
            'name': action.action_name,
            'description': action.description,
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': [key for key, val in action.params_in.items() if val.required],
            }
        })
    return actions_out


def get_param_format(param: Parameter | Parameter.ArrayItems) -> Dict:
    # Check if the parameter is of type array
    print(param)
    if param.type == "array":
        # Handle the array type by specifying its items
        return {
            'type': 'array',
            'items': get_param_format(param.items),
            'description': ''
        }
    else:
        # Handle non-array types as before
        return {'type': param.type, 'description': ''}
