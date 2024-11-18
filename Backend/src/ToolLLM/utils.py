import jsonref


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
