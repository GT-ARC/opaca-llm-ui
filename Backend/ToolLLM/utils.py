from typing import List, Dict
from Backend.RestGPT import Parameter


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


def get_param_format(param: Parameter) -> Dict:
    # Check if the parameter is of type array
    if param.type == "array":
        # Handle the array type by specifying its items
        return {
            'type': 'array',
            'items': {
                'type': param.items.type,  # Use the type from ArrayItems
                'description': ''
            },
            'description': ''
        }
    else:
        # Handle non-array types as before
        return {'type': param.type, 'description': ''}
