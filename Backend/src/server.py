"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available  LLM prompting methods that can be used,
and different routes for posting questions, updating the configuration, etc.
"""
import os
from pathlib import Path
from typing import Dict, Any, List
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket

from .utils import validate_config_input, exception_to_result
from .models import ConnectRequest, QueryRequest, QueryResponse, ConfigPayload, Chat, \
    SearchResult, get_supported_models
from .simple import SimpleMethod
from .simple_tools import SimpleToolsMethod
from .toolllm import ToolLLMMethod
from .orchestrated import SelfOrchestratedMethod
from .file_utils import delete_file_from_all_clients, save_file_to_disk, FILES_PATH
from .session_manager import handle_session_id, delete_all_sessions, cleanup_old_sessions, \
    store_sessions_in_db, handle_chat_id, create_chat_name, update_chat_time, store_message

# Configure CORS settings
origins = os.getenv('CORS_WHITELIST', 'http://localhost:5173').split(";")


METHODS = {
    SimpleMethod.NAME: SimpleMethod,
    SimpleToolsMethod.NAME: SimpleToolsMethod,
    ToolLLMMethod.NAME: ToolLLMMethod,
    SelfOrchestratedMethod.NAME: SelfOrchestratedMethod,
}


logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def session_task():
        await cleanup_old_sessions()
        await store_sessions_in_db()

    # before start
    asyncio.create_task(session_task())

    try:
        # app running
        yield
    finally:
        # on shutdown
        logger.info("Saving sessions to DB...")
        await asyncio.wait_for(asyncio.shield(store_sessions_in_db()), timeout=10)


app = FastAPI(
    title="OPACA LLM Backend Services",
    summary="Provides services for interacting with the OPACA LLM. Mainly to be used by the frontend, but can also be called directly.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/methods", description="Get list of available LLM-prompting-methods, to be used as parameter for other routes.")
async def get_methods() -> list:
    return list(METHODS)


@app.get("/models", description="Get supported models, grouped by LLM server URL")
async def get_models() -> dict[str, list[str]]:
    return {
        url: models
        for url, _key, models in get_supported_models()
    }


@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: Response, connect: ConnectRequest) -> int:
    session = await handle_session_id(request, response)
    return await session.opaca_client.connect(connect.url, connect.user, connect.pwd)


@app.get("/connection", description="Get URL of currently connected OPACA Runtime Platform, if any, or null.")
async def get_connection(request: Request, response: Response) -> str | None:
    session = await handle_session_id(request, response)
    return session.opaca_client.url


@app.post("/disconnect", description="Reset OPACA Runtime Connection.")
async def disconnect(request: Request, response: Response) -> Response:
    session = await handle_session_id(request, response)
    await session.opaca_client.disconnect()
    return Response(status_code=204)


@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform, grouped by Agent, using the same format as the OPACA platform itself.")
async def get_actions(request: Request, response: Response) -> dict[str, List[Dict[str, Any]]]:
    session = await handle_session_id(request, response)
    return await session.opaca_client.get_actions_simple()


@app.post("/query/{method}", description="Send message to the given LLM method. Returns the final LLM response along with all intermediate messages and different metrics. This method does not include, nor is the message and response added to, any chat history.")
async def query_no_history(request: Request, response: Response, method: str, message: QueryRequest) -> QueryResponse:
    session = await handle_session_id(request, response)
    session.abort_sent = False
    try:
        return await METHODS[method](session).query(message.user_query, Chat(chat_id=''))
    except Exception as e:
        return exception_to_result(message.user_query, e)


@app.post("/stop", description="Abort generation for every query of the current session.")
async def stop_query(request: Request, response: Response) -> None:
    session = await handle_session_id(request, response)
    session.abort_sent = True


@app.post("/reset_all", description="Reset all sessions (message histories and configurations)")
async def reset_all():
    await delete_all_sessions()

### CHAT ROUTES

@app.get("/chats", description="Get available chats, just their names and IDs, but NOT the messages.")
async def get_chats(request: Request, response: Response) -> List[Chat]:
    session = await handle_session_id(request, response)
    chats = [
        Chat(chat_id=chat.chat_id, name=chat.name, time_created=chat.time_created, time_modified=chat.time_modified)
        for chat in session.chats.values()
    ]
    chats.sort(key=lambda chat: chat.time_modified, reverse=True)
    return chats


@app.get("/chats/{chat_id}", description="Get a chat's full history (including user queries, LLM responses, internal/intermediate messages, metrics, etc.).")
async def get_chat_history(request: Request, response: Response, chat_id: str) -> Chat:
    session = await handle_session_id(request, response)
    chat = await handle_chat_id(session, chat_id)
    return chat


@app.post("/chats/{chat_id}/query/{method}", description="Send message to the given LLM method; the history is stored in the backend and will be sent to the actual LLM along with the new message. Returns the final LLM response along with all intermediate messages and different metrics.")
async def query_chat(request: Request, response: Response, method: str, chat_id: str, message: QueryRequest) -> QueryResponse:
    session = await handle_session_id(request, response)
    chat = await handle_chat_id(session, chat_id, True)
    await create_chat_name(chat, message)
    session.abort_sent = False
    result = None
    try:
        result = await METHODS[method](session).query(message.user_query, chat)
    except Exception as e:
        result = exception_to_result(message.user_query, e)
    finally:
        await store_message(chat, result)
        return result


@app.websocket("/chats/{chat_id}/stream/{method}")
async def query_stream(websocket: WebSocket, chat_id: str, method: str):
    await websocket.accept()
    session = await handle_session_id(websocket)
    chat = await handle_chat_id(session, chat_id, True)
    session.abort_sent = False
    message = None
    result = None
    try:
        data = await websocket.receive_json()
        message = QueryRequest(**data)
        await create_chat_name(chat, message)
        result = await METHODS[method](session, websocket).query_stream(message.user_query, chat)
    except Exception as e:
        result = exception_to_result(message.user_query, e)
    finally:
        await store_message(chat, result)
        await websocket.send_json(result.model_dump_json())
        await websocket.close()


@app.put("/chats/{chat_id}", description="Update a chat's name.")
async def update_chat(request: Request, response: Response, chat_id: str, new_name: str) -> None:
    session = await handle_session_id(request, response)
    chat = await handle_chat_id(session, chat_id)
    chat.name = new_name
    await update_chat_time(chat)


@app.delete("/chats/{chat_id}", description="Delete a single chat.")
async def delete_chat(request: Request, response: Response, chat_id: str) -> bool:
    session = await handle_session_id(request, response)
    return await delete_chat(session, chat_id)


@app.post("/chats/search", description="Search through all chats for a given query.")
async def search_chats(request: Request, response: Response, query: str) -> Dict[str, List[SearchResult]]:
    def make_excerpt(text: str, query: str, index: int, buffer_length: int = 30) -> str:
        start = max(0, index - buffer_length)
        stop = min(len(text), index + len(query) + buffer_length)
        excerpt = message.content[start:stop]
        if start > 0:
            excerpt = f'...{excerpt}'
        if stop < len(text):
            excerpt = f'{excerpt}...'
        return excerpt

    if len(query) < 1: return {}
    session = await handle_session_id(request, response)
    results = {}
    query = query.lower()
    for chat in session.chats.values():
        for message_id, message in enumerate(chat.messages):
            index = -1
            while (index := message.content.lower().find(query, index+1)) >= 0:
                if chat.chat_id not in results:
                    results[chat.chat_id] = []
                results[chat.chat_id].append(SearchResult(
                    chat_id=chat.chat_id,
                    chat_name=chat.name,
                    message_id=message_id,
                    excerpt=make_excerpt(message.content, query, index),
                ))

    return results

## CONFIG ROUTES

@app.get("/config/{method}", description="Get current configuration of the given prompting method.")
async def get_config(request: Request, response: Response, method: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    if method not in session.config:
        session.config[method] = METHODS[method].default_config()
    return ConfigPayload(config_values=session.config[method], config_schema=METHODS[method].config_schema())


@app.put("/config/{method}", description="Update configuration of the given prompting method.")
async def set_config(request: Request, response: Response, method: str, conf: dict) -> ConfigPayload:
    session = await handle_session_id(request, response)
    try:
        validate_config_input(conf, METHODS[method].config_schema())
    except HTTPException as e:
        raise e
    session.config[method] = conf
    return ConfigPayload(config_values=session.config[method], config_schema=METHODS[method].config_schema())


@app.delete("/config/{method}", description="Resets the configuration of the prompting method to its default.")
async def reset_config(request: Request, response: Response, method: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    session.config[method] = METHODS[method].default_config()
    return ConfigPayload(config_values=session.config[method], config_schema=METHODS[method].config_schema())

## FILE ROUTES

@app.get("/files", description="Get a list of all uploaded files.")
async def get_files(request: Request, response: Response) -> dict:
    session = await handle_session_id(request, response)
    return session.uploaded_files


@app.post("/files", description="Upload a file to the backend, to be sent to the LLM for consideration "
                                "with the next user queries. Currently only supports PDF.")
async def upload_files(request: Request, response: Response, files: List[UploadFile]):
    session = await handle_session_id(request, response)
    uploaded = []
    for file in files:
        try:
            file_path = Path(FILES_PATH, session.session_id, file.filename)
            filedata = await save_file_to_disk(file, file_path)
            session.uploaded_files[filedata.file_id] = filedata
            uploaded.append(filedata)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file {file.filename}: {str(e)}"
            )

    return {"uploaded_files": uploaded}


@app.delete("/files/{file_id}", description="Delete an uploaded file.")
async def delete_file(request: Request, response: Response, file_id: str) -> bool:
    session = await handle_session_id(request, response)
    files = session.uploaded_files

    if file_id in files:
        result = await delete_file_from_all_clients(session, file_id)
        return result

    return False


@app.patch("/files/{file_id}", description="Mark a file as suspended or unsuspended.")
async def update_file(request: Request, response: Response, file_id: str, suspend: bool) -> bool:
    session = await handle_session_id(request, response)
    files = session.uploaded_files

    if file_id in files:
        file = files[file_id]
        file.suspended = suspend
        return True

    return False


# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
