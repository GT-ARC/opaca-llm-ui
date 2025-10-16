import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type
import asyncio
import jsonref

import httpx
from pydantic import BaseModel

from .models import ConfigParameter, SessionData, QueryResponse, AgentMessage, ChatMessage, OpacaException, Chat, \
    ToolCall, get_supported_models, ContainerLoginNotification, ContainerLoginResponse
from .file_utils import upload_files

logger = logging.getLogger(__name__)


class AbstractMethod(ABC):
    NAME: str

    def __init__(self, session: SessionData, streaming=False):
        self.session = session
        self.streaming = streaming

    @classmethod
    def config_schema(cls) -> Dict[str, ConfigParameter]:
        pass

    @staticmethod
    def make_llm_config_param(name: Optional[str] = None, description: Optional[str] = None):
        models = [f"{url}::{model}" for url, _, models in get_supported_models() for model in models]
        return ConfigParameter(
            name=name,
            description=description,
            type="string",
            required=True,
            default=models[0],
            enum=models,
            free_input=True,
        )

    @classmethod
    def default_config(cls):
        def extract_defaults(schema):
            # Extracts the default values of nested configurations
            if isinstance(schema, ConfigParameter):
                if schema.type == 'object' and isinstance(schema.default, dict):
                    return {key: extract_defaults(value) for key, value in schema.default.items()}
                else:
                    return schema.default
            else:
                return schema

        return {key: extract_defaults(value) for key, value in cls.config_schema().items()}


    @abstractmethod
    async def query(self, message: str, chat: Chat) -> QueryResponse:
        pass


    async def call_llm(
            self,
            model: str,
            agent: str,
            system_prompt: str,
            messages: List[ChatMessage],
            temperature: Optional[float] = .0,
            tools: Optional[List[Dict[str, Any]]] = None,
            tool_choice: Optional[str] = "auto",
            response_format: Optional[Type[BaseModel]] = None,
    ) -> AgentMessage:
        """
        Calls an LLM with given parameters, including support for streaming, tools, file uploads, and response schema parsing.

        Args:
            model (str): LLM host AND model name (e.g., "https://...: gpt-4-turbo"), from config.
            agent (str): The agent name (e.g. "simple-tools").
            system_prompt (str): The system prompt to start the conversation.
            messages (List[ChatMessage]): The list of chat messages.
            temperature (float): The model temperature to use.
            tools (Optional[List[Dict]]): List of tool definitions (functions).
            tool_choice (Optional[str]): Whether to force tool use ("auto", "none", "only", or "required").
            response_format (Optional[Type[BaseModel]]): Optional Pydantic schema to validate response.

        Returns:
            AgentMessage: The final message returned by the LLM with metadata.
        """
        try:
            url, model = map(str.strip, model.split("::"))
        except Exception:
            raise Exception(f"Invalid format: Must be '<llm-host>::<model>': {model}")
        client = self.session.llm_client(url)

        # Initialize variables
        exec_time = time.time()
        tool_call_buffers = {}
        content = ''
        agent_message = AgentMessage(agent=agent, content='', tools=[])

        file_message_parts = await upload_files(self.session, url)

        # Modify the last user message to include file parts
        if file_message_parts:
            messages[-1].content = [*file_message_parts, {"type": "input_text", "text": messages[-1].content}]

        # Set a custom response format schema if provided, else expect plain text
        r_format = transform_schema(response_format.model_json_schema()) if response_format else \
            {'format': {'type': 'text'}}

        # Set settings for model invocation
        kwargs = {
            'model': model,
            'input': [ChatMessage(role="system", content=system_prompt), *messages],
            'tools': tools or [],
            'tool_choice': tool_choice if tools else 'none',
            'text': r_format,
            'stream': True
        }

        # If tool_choice is set to "only", use "auto" for external API call
        if tool_choice == "only":
            kwargs['tool_choice'] = 'auto'

        # o1/o3/o4/gpt-5 don't support temperature param
        if not model.startswith(('o1', 'o3', 'o4', 'gpt-5')):
            kwargs['temperature'] = temperature

        # Main stream logic
        stream = await client.responses.create(**kwargs)
        async for event in stream:

            # Check if an "abort" message has been sent by the user
            if self.session.abort_sent:
                raise OpacaException(
                    user_message="(The generation of the response has been stopped.)",
                    error_message="Completion generation aborted by user. See Debug/Logging Tab to see what has been done so far."
                )

            # New tool call generation started, including the complete function call name
            if event.type == 'response.output_item.added' and event.item.type == 'function_call':
                agent_message.tools.append(ToolCall(name=event.item.name, id=event.output_index))
                tool_call_buffers[event.output_index] = ""

            # Tool call argument chunk received
            elif event.type == 'response.function_call_arguments.delta':
                # We assume that the entry has been created already
                tool_call_buffers[event.output_index] += event.delta

            # Final tool call chunk received
            elif event.type == 'response.function_call_arguments.done':
                # Try to transform function arguments into JSON
                try:
                    agent_message.tools[-1].args = json.loads(tool_call_buffers[event.output_index])
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse tool arguments: {tool_call_buffers[event.output_index]}")
                    agent_message.tools[-1].args = {}

            # Plain text chunk received
            elif event.type == 'response.output_text.delta':
                if tool_choice == "only":
                    break
                agent_message.content = event.delta
                content += event.delta

            # Final message received
            elif event.type == 'response.completed':
                # If a response format was provided, try to cast the response to the provided schema
                if response_format:
                    try:
                        agent_message.formatted_output = response_format.model_validate_json(content)
                    except json.decoder.JSONDecodeError:
                        raise OpacaException("An error occurred while parsing a response JSON", error_message="An error occurred while parsing a response JSON", status_code=500)
                # Capture token usage
                agent_message.response_metadata = event.response.usage.to_dict()

            if self.session.has_websocket() and self.streaming:
                await self.send_to_websocket(agent_message)
                agent_message.content = ''

        agent_message.execution_time = time.time() - exec_time

        # Final stream to transmit execution time and response metadata
        if self.session.has_websocket() and self.streaming:
            agent_message.content = ''
            await self.send_to_websocket(agent_message)

        agent_message.content = content

        logger.info(agent_message.content or agent_message.tools or agent_message.formatted_output, extra={"agent_name": agent})

        return agent_message


    async def send_to_websocket(self, message: BaseModel):
        if self.session.has_websocket() and self.streaming:
            await self.session.websocket_send(message)


    async def invoke_tool(self, tool_name: str, tool_args: dict, tool_id: int, login_attempt_retry: bool = False) -> ToolCall:
        """
        Invoke OPACA action matching the given tool. If invoke fails due to required login, attempt Login (via websocket callback)
        and try again. In any case returns a ToolCall, where "result" can be error message.
        """
        if "--" in tool_name:
            agent_name, action_name = tool_name.split('--', maxsplit=1)
        else:
            agent_name, action_name = None, tool_name

        try:
            t_result = await self.session.opaca_client.invoke_opaca_action(
                action_name,
                agent_name,
                tool_args,
            )
        except httpx.HTTPStatusError as e:
            res = e.response.json()
            t_result = f"Failed to invoke tool.\nStatus code: {e.response.status_code}\nResponse: {e.response.text}\nResponse JSON: {res}"
            cause = res.get("cause", {}).get("message", "")
            status = res.get("cause", {}).get("statusCode", -1)
            if self.session.has_websocket() and (status in [401, 403] or ("401" in cause or "403" in cause or "credentials" in cause)):
                return await self.handleContainerLogin(agent_name, action_name, tool_name, tool_args, tool_id, login_attempt_retry)
        except Exception as e:
            t_result = f"Failed to invoke tool.\nCause: {e}"

        return ToolCall(id=tool_id, name=tool_name, args=tool_args, result=t_result)


    async def get_tools(self, max_tools=128) -> tuple[list[dict], str]:
        """
        Get list of available actions as OpenAI Functions. This primarily includes the OPACA actions, but can also include "internal" tools.
        """
        tools, error = openapi_to_functions(await self.session.opaca_client.get_actions_openapi(inline_refs=True))
        if len(tools) > max_tools:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of {max_tools}. All tools after index {max_tools} will be ignored!\n")
            tools = tools[:max_tools]
        return tools, error


    async def handleContainerLogin(self, agent_name: str, action_name: str, tool_name: str, tool_args: dict, tool_id: int, login_attempt_retry: bool = False):
        """Handles failed tool invocation due to missing credentials."""

        # If a "missing credentials" error is encountered, initiate container login
        container_id, container_name = await self.session.opaca_client.get_most_likely_container_id(agent_name, action_name)

        # Get credentials from user
        await self.session.websocket_send(ContainerLoginNotification(
            container_name=container_name,
            tool_name=tool_name,
            retry=login_attempt_retry
        ))
        response = ContainerLoginResponse(**await self.session.websocket_receive())

        # Check if credentials were provided
        if not response.username or not response.password:
            return ToolCall(id=tool_id, name=tool_name, args=tool_args,
                            result=f"Failed to invoke tool.\nNo credentials provided.")

        # Send credentials to container via OPACA
        await self.session.opaca_client.container_login(response.username, response.password, container_id)

        # Sleep 1 second before attempting tool retry
        await asyncio.sleep(1)

        # try to invoke the tool again
        res = await self.invoke_tool(tool_name, tool_args, tool_id, True)

        # auto-logout after some time
        asyncio.create_task(self.session.opaca_client.deferred_container_logout(container_id, response.timeout))

        return res


    @classmethod
    def validate_config_input(cls, values: Dict[str, Any]):
        """
        Validates the given input values against the Configuration Schema
        :param values: The input dict of configuration parameters that was sent by the UI
        :return: Returns nothing if everything was successfully validated, raises Exception otherwise
        """
        schema = cls.config_schema()

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




def openapi_to_functions(openapi_spec, agent: str | None = None, strict: bool = False):
    """
    Convert OpenAPI REST specification (with inlined references) to OpenAI Function specification.

    Parameters:
    - openapi_spec: the OpenAPI specification
    - agent: name of OPACA agent to filter for, or None for all
    - strict: make all action parameters required (needed for some models)
    """
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
