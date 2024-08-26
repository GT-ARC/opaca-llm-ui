from typing import List


def transform_to_openai_tools(action_list: List) -> List:
    actions_out = []
    for action in action_list:
        properties = {key: {'type': val.type, 'description': ''} for key, val in action.params_in.items()}

        for c_name, c_val in action.custom_params.items():
            # This uses 'lower()' because parameter names are normally lower case but the
            # custom parameters are typically upper case but a replacement needs to occur
            properties[c_name.lower()] = {
                'type': 'object',
                'properties': {key: {'type': val.type, 'description': ''} for key, val in c_val.items()},
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
