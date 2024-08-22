from typing import List


def transform_to_openai_tools(action_list: List) -> List:
    actions_out = []
    for action in action_list:
        actions_out.append({
            'name': action.action_name,
            'description': action.description,
            'parameters': {
                'type': 'object',
                'properties': {key: {'type': val.type, 'description': ''} for key, val in action.params_in.items()},
                'required': [key for key, val in action.params_in.items() if val.required],
            }
        })
    return actions_out
