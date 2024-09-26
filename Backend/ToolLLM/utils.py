import jsonref


def openapi_to_functions(openapi_spec, use_agent_names: bool = False):
    functions = []

    for path, methods in openapi_spec["paths"].items():
        for method, spec_with_ref in methods.items():
            # 1. Resolve JSON references.
            spec = jsonref.replace_refs(spec_with_ref)

            # 2. Extract a name for the functions
            # The operation id is formatted as 'containerId-agentName-actionName'
            container_id, agent_name, function_name = spec.get("operationId").split(';')

            # 3. Extract a description and parameters.
            desc = spec.get("description")[:1024] or spec.get("summary", "")[:1024]

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

    return functions
