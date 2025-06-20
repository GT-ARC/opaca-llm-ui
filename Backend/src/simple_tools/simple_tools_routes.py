import logging
import time

from starlette.websockets import WebSocket
from fastapi import Form, File, UploadFile
from typing import List, Optional
import json

from ..abstract_method import AbstractMethod
from ..models import Response, AgentMessage, SessionData, ConfigParameter, ChatMessage
from ..utils import openapi_to_functions


system_prompt = """You are a helpful ai assistant who answers user queries with the help of 
tools. You can find those tools in the tool section. Do not generate optional 
parameters for those tools if the user has not explicitly told you to. 
Some queries require sequential calls with those tools. In this case, you will receive the results of tool calls of 
previous iterations. Evaluate, whether another tool call if necessary. 
If tools return nothing or simply complete without feedback 
you should still tell the user that. Once you have retrieved all necessary information, immediately generate a response 
to the user about the result and the retrieval process. 
If you are unable to fulfill the user queries with the given tools, let the user know. 
You are only allowed to use those given tools. If a user asks about tools directly, 
answer them with the required information. Tools can also be described as services. 
"""


logger = logging.getLogger("src.models")

class SimpleToolsBackend(AbstractMethod):
    NAME = "simple-tools"

    async def query(self, message: str, session: SessionData) -> Response:
        return await self.query_stream(message, session)

    async def query_stream(self, message: str, session: SessionData, websocket: WebSocket = None) -> Response:
        logger.info(message, extra={"event": "query_stream getriggert"})
        exec_time = time.time()
        logger.info(message, extra={"agent_name": "user"})
        result = Response(query=message)

        config = session.config.get(self.NAME, self.default_config())
        
        # Get tools and transform them into the OpenAI Function Schema
        try:
            tools, error = openapi_to_functions(await session.opaca_client.get_actions_with_refs(), config['use_agent_names'])
        except AttributeError as e:
            result.error = str(e)
            result.content = "ERROR: It seems you are not connected to a running OPACA platform!"
            return result
        if len(tools) > 128:
            error += (f"WARNING: Your number of tools ({len(tools)}) exceeds the maximum tool limit "
                      f"of 128. All tools after index 128 will be ignored!\n")
            tools = tools[:128]

        # initialize message history
        messages = session.messages.copy()
        messages.append(ChatMessage(role="user", content=message))
                   
        while result.iterations < 10:

            result.iterations += 1

            # call the LLM with function-calling enabled
            response = await self.call_llm(
                client=session.llm_clients[config["vllm_base_url"]],
                model=config["model"],
                agent="assistant",
                system_prompt=system_prompt,
                messages=messages,
                temperature=config["temperature"],
                tools=tools,
                websocket=websocket,
            )

            # record assistant message
            result.agent_messages.append(AgentMessage(
                agent="assistant",
                content=response.content,
                response_metadata=response.response_metadata,
                execution_time=response.execution_time,
            ))

            try:
                if not response.tools:
                    result.content = response.content
                    break

                tool_contents = ""
                tool_entries = []
                
                for call in response.tools:
                    if config['use_agent_names']:
                        agent_name, action_name = call['name'].split('--', maxsplit=1)
                    else:
                        agent_name = None
                        action_name = call['name']
                    params = call["args"].get("requestBody", {})
                
                    # invoke via OPACA client
                    try:
                        action_result = await session.opaca_client.invoke_opaca_action(
                            action_name, agent=agent_name, params=params
                        )
                    except Exception as e:
                        action_result = None
                        result.error += f"Failed to invoke action {action_name}. Cause: {e}"
                
                    # collect tool result details
                    tool_contents += f"The result of tool '{action_name}' with parameters '{params}' was: {action_result}\n"
                    tool_entries.append({
                        "id": result.iterations,
                        "name": call["name"],
                        "args": params,
                        "result": action_result
                    })
                
                # Append one unified message after loop
                if tool_contents:
                    messages.append(ChatMessage(role="user",
                                                content=f"A user had the following request: {message}\n"
                                                        f"You have used the following tools: \n{tool_contents}"))
                    result.agent_messages[-1].tools = tool_entries
                
            except Exception as e:
                error = f"There was an error in simple_tools_routes: {e}"
                messages.append(ChatMessage(role="system", content=error))
                result.agent_messages.append(AgentMessage(agent="system", content=error))
                result.error = str(e)

        result.execution_time = time.time() - exec_time
        return result
    
    async def upload_files(
        self,
        session: SessionData,
        json_data: str,
        files: Optional[List[UploadFile]] = None
    ):
        logger.info("Backend upload_files triggered")

        # --- Parse user message from form field ---
        try:
            message_data = json.loads(json_data)
            user_query = message_data.get("user_query", "")
            api_key = message_data.get("api_key", "")
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}"}

        # --- Read uploaded files into session memory ---
        uploaded_file_map = {}
        if files:
            for uploaded_file in files:
                content = await uploaded_file.read()
                uploaded_file_map[uploaded_file.filename] = {
                    "filename": uploaded_file.filename,
                    "content_type": uploaded_file.content_type,
                    "content": content
                }
                logger.info(f"Received file: {uploaded_file.filename} ({len(content)} bytes)")

        # --- Store files in session for later use by tools ---
        session.uploaded_files = uploaded_file_map

        # --- Get model config ---
        config = session.config.get(self.NAME, self.default_config())

        # --- Get tool definitions ---
        result = Response(query=user_query)
        #logger.info("opaca_client:", session.opaca_client)
        #logger.info("opaca_client:", session)
        try:
            tools, error = openapi_to_functions(
                await session.opaca_client.get_actions_with_refs(),
                config['use_agent_names']
            )
        except AttributeError as e:
            result.error = str(e)
            result.content = "ERROR: It seems you are not connected to a running OPACA platform!"
            return result

        if len(tools) > 128:
            error += f"WARNING: You have {len(tools)} tools, truncating to 128"
            tools = tools[:128]

        # --- Set up chat history ---
        messages = session.messages.copy()
        messages.append(ChatMessage(role="user", content=user_query))

        # --- Iterative tool + LLM loop ---
        logger.info("simple tools is running")
        while result.iterations < 10:
            result.iterations += 1

            # --- Call LLM with function-calling enabled ---
            if not uploaded_file_map:
                logger.info("No files uploaded, using normal call_llm")
                response = await self.call_llm(
                    client=session.llm_clients[config["vllm_base_url"]],
                    model=config["model"],
                    agent="assistant",
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=config["temperature"],
                    tools=tools,
                    websocket=None  # No streaming for upload_files
                )

            else:
                logger.info(f"Files uploaded: {list(uploaded_file_map.keys())}")

                # Check all files are PDFs
                all_pdfs = all(
                    f["content_type"] == "application/pdf" or f["filename"].lower().endswith(".pdf")
                    for f in uploaded_file_map.values()
                )

                if not all_pdfs:
                    logger.info("Non-PDF file detected. Returning error.")
                    return {"error": "Only PDF files are supported for file uploads."}

                # For now, take the first PDF only
                first_file_info = next(iter(uploaded_file_map.values()))
                pdf_content = first_file_info["content"]

                # Save to a temp file (optional: depends on how your call_llm_with_pdf expects it)
                tmp_pdf_path = f"/tmp/{first_file_info['filename']}"
                with open(tmp_pdf_path, "wb") as f:
                    f.write(pdf_content)

                logger.info(f"Using call_llm_with_pdf for: {first_file_info['filename']}")

                response = await self.call_llm_with_pdf(
                    client=session.llm_clients[config["vllm_base_url"]],
                    model=config["model"],
                    agent="assistant",
                    system_prompt=system_prompt,
                    user_question=user_query,
                    pdf_file_path=tmp_pdf_path,
                    temperature=config["temperature"],
                    tools=tools
                )


            # --- Save assistant message ---
            messages.append(ChatMessage(role="assistant", content=response.content))
            result.agent_messages.append(AgentMessage(
                agent="assistant",
                content=response.content,
                response_metadata=response.response_metadata,
                execution_time=response.execution_time
            ))

            # --- Handle any tool calls ---
            try:

                if not response.tools:
                    result.content = response.content
                    break

                tool_contents = []
                tool_entries = []

                tool_contents = []
                tool_entries = []

                for call in response.tools:
                    action_name = call["name"]
                    params = call["args"].get("requestBody", {})

                    # Tool may refer to uploaded files by name
                    # You can access files via: session.uploaded_files.get(filename)

                    action_result = await session.opaca_client.invoke_opaca_action(
                        action_name,
                        agent=None,
                        params=params
                    )

                    tool_contents.append(f"The result of tool '{action_name}' was: {repr(action_result)}")
                    tool_entries.append({
                        "id": result.iterations,
                        "name": call["name"],
                        "args": params,
                        "result": action_result
                    })

                # Append unified tool result to messages
                if tool_contents:
                    combined_tool_response = "\n".join(tool_contents)
                    messages.append(ChatMessage(role="assistant", content=combined_tool_response))
                    result.agent_messages.append(AgentMessage(
                        agent="assistant",
                        content=combined_tool_response,
                        tools=tool_entries
                    ))

            except Exception as e:
                error = f"There was an error during tool invocation: {e}"
                messages.append(ChatMessage(role="system", content=error))
                result.agent_messages.append(AgentMessage(agent="system", content=error))
                result.error = str(e)
                break

        result.content = response.content
        result.execution_time = time.time() - result.execution_time

        # --- Update session message history ---
        session.messages.extend([
            ChatMessage(role="user", content=user_query),
            ChatMessage(role="assistant", content=result.content)
        ])

        # --- Return final assistant message only (no files, no metadata) ---
        return result

    @property
    def config_schema(self) -> dict:
        return {
            "model": ConfigParameter(type="string", required=True, default="gpt-4o"),
            "temperature": ConfigParameter(type="number", required=True, default=0.0, minimum=0.0, maximum=2.0),
            "use_agent_names": ConfigParameter(type="boolean", required=False, default=True),
            "vllm_base_url": ConfigParameter(type="string", required=False, default='gpt'),
        }
