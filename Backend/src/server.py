"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM prompting methods that can be used,
and different routes for posting questions, updating the configuration, etc.
"""
import os
import uuid
from datetime import datetime, UTC
from typing import Dict, Any
import asyncio
import logging
import time
from contextlib import asynccontextmanager

import io
from fastapi import FastAPI, Request, HTTPException, UploadFile
from fastapi import Response as FastAPIResponse
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
from starlette.websockets import WebSocket

from typing import List, Union

from .utils import validate_config_input, exception_to_result
from .models import ConnectInfo, Message, Response, SessionData, ConfigPayload, ChatMessage, OpacaFile, Chat
from .toolllm import *
from .simple import SimpleBackend
from .simple_tools import SimpleToolsBackend
from .opaca_client import OpacaClient
from .orchestrated import SelfOrchestratedBackend


@asynccontextmanager
async def lifespan(app):
    # before start
    asyncio.create_task(cleanup_old_sessions())
    # app running
    yield
    # after shutdown
    pass

app = FastAPI(
    title="OPACA LLM Backend Services",
    summary="Provides services for interacting with the OPACA LLM. Mainly to be used by the frontend, but can also be called directly.",
    lifespan=lifespan
)

# Configure CORS settings
origins = os.getenv('CORS_WHITELIST', 'http://localhost:5173').split(";")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BACKENDS = {
    SimpleBackend.NAME: SimpleBackend(),
    SelfOrchestratedBackend.NAME: SelfOrchestratedBackend(),
    ToolLLMBackend.NAME: ToolLLMBackend(),
    SimpleToolsBackend.NAME: SimpleToolsBackend(),
}


# Simple dict to store session data
# Keep in mind: The session data is only reset upon restarting the application
sessions_lock = asyncio.Lock()
sessions: Dict[str, SessionData] = {}

logger = logging.getLogger("uvicorn")


@app.get("/backends", description="Get list of available 'backends'/LLM-prompting-methods, to be used as parameter for other routes.")
async def get_backends() -> list:
    return list(BACKENDS)


@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: FastAPIResponse, connect: ConnectInfo) -> int:
    session = await handle_session_id(request, response)
    return await session.opaca_client.connect(connect.url, connect.user, connect.pwd)


@app.post("/disconnect", description="Reset OPACA Runtime Connection.")
async def disconnect(request: Request, response: FastAPIResponse) -> FastAPIResponse:
    session = await handle_session_id(request, response)
    await session.opaca_client.disconnect()
    return FastAPIResponse(status_code=204)


@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform, grouped by Agent, using the same format as the OPACA platform itself.")
async def actions(request: Request, response: FastAPIResponse) -> dict[str, List[Dict[str, Any]]]:
    session = await handle_session_id(request, response)
    return await session.opaca_client.get_actions_simple()


@app.post("/upload", description="Upload a file to be backend, to be sent to the LLM for consideration with the next user queries. Currently only supports PDF.")
async def upload_files(request: Request, response: FastAPIResponse, files: List[UploadFile]):
    session = await handle_session_id(request, response)
    uploaded = []
    for file in files:
        try:
            contents = await file.read()

            file_model = OpacaFile(
                content_type=file.content_type,
                sent=False
            )
            file_model._content = io.BytesIO(contents)

            # Store in session.uploaded_files
            session.uploaded_files[file.filename] = file_model
            uploaded.append(file.filename)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file {file.filename}: {str(e)}"
            )

    return JSONResponse(status_code=201, content={"uploaded_files": uploaded})


@app.post("/query/{backend}", description="Send message to the given LLM backend. Returns the final LLM response along with all intermediate messages and different metrics.")
async def query(request: Request, response: FastAPIResponse, backend: str, message: Message) -> Response:
    session = await handle_session_id(request, response)
    session.abort_sent = False
    try:
        await BACKENDS[backend].init_models(session)
        return await BACKENDS[backend].query(message.user_query, session, Chat(chat_id=''))
    except Exception as e:
        return exception_to_result(message.user_query, e)


@app.post("/stop", description="Abort generation for every query of the current session.")
async def stop_query(request: Request, response: FastAPIResponse) -> None:
    session = await handle_session_id(request, response)
    session.abort_sent = True

### CHAT ROUTES

@app.get("/chats", description="Get available chats, just their names and IDs, but NOT the messages.")
async def get_chats(request: Request, response: FastAPIResponse) -> List[Chat]:
    session = await handle_session_id(request, response)
    chats = [
        Chat(chat_id=chat.chat_id, name=chat.name, time_created=chat.time_created, time_modified=chat.time_modified)
        for chat in session.chats.values()
    ]
    chats.sort(key=lambda chat: chat.time_modified, reverse=True)
    return chats


@app.get("/chats/{chat_id}", description="Get a chat's full history (user queries and LLM responses, no internal/intermediate messages).")
async def get_chat_history(request: Request, response: FastAPIResponse, chat_id: str) -> Chat:
    session = await handle_session_id(request, response)
    chat = handle_chat_id(session, chat_id)
    return chat


@app.post("/chats/{chat_id}/query/{backend}", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message. Returns the final LLM response along with all intermediate messages and different metrics.")
async def query(request: Request, response: FastAPIResponse, backend: str, chat_id: str, message: Message) -> Response:
    session = await handle_session_id(request, response)
    chat = handle_chat_id(session, chat_id)
    create_chat_name(chat, message)
    session.abort_sent = False
    result = None
    try:
        await BACKENDS[backend].init_models(session)
        result = await BACKENDS[backend].query(message.user_query, session, chat)
    except Exception as e:
        result = exception_to_result(message.user_query, e)
    finally:
        await store_message(chat, message, result)
        return result


@app.websocket("/chats/{chat_id}/stream/{backend}")
async def query_stream(websocket: WebSocket, chat_id: str, backend: str):
    await websocket.accept()
    session = await handle_session_id(websocket)
    chat = handle_chat_id(session, chat_id, True)
    session.abort_sent = False
    message = None
    result = None
    try:
        data = await websocket.receive_json()
        message = Message(**data)
        create_chat_name(chat, message)
        await BACKENDS[backend].init_models(session)
        result = await BACKENDS[backend].query_stream(message.user_query, session, chat, websocket)
    except Exception as e:
        result = exception_to_result(message.user_query, e)
    finally:
        await store_message(chat, message, result)
        await websocket.send_json(result.model_dump_json())
        await websocket.close()


@app.put("/chats/{chat_id}", description="Update a chat's name.")
async def update_chat(request: Request, response: FastAPIResponse, chat_id: str, new_name: str) -> None:
    session = await handle_session_id(request, response)
    chat = handle_chat_id(session, chat_id)
    chat.name = new_name
    update_chat_time(chat)


@app.delete("/chats/{chat_id}", description="Delete a single chat.")
async def delete_chat(request: Request, response: FastAPIResponse, chat_id: str) -> bool:
    session = await handle_session_id(request, response)
    chat = handle_chat_id(session, chat_id)
    if chat is not None:
        async with sessions_lock:
            del session.chats[chat_id]
        return True
    else:
        return False


@app.post("/reset_all", description="Reset all sessions (message histories and configurations)")
async def reset_all():
    async with sessions_lock:
        sessions.clear()

## CONFIG ROUTES

@app.get("/config/{backend}", description="Get current configuration of the given prompting method.")
async def get_config(request: Request, response: FastAPIResponse, backend: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    if backend not in session.config:
        session.config[backend] = BACKENDS[backend].default_config()
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)


@app.put("/config/{backend}", description="Update configuration of the given prompting method.")
async def set_config(request: Request, response: FastAPIResponse, backend: str, conf: dict) -> ConfigPayload:
    session = await handle_session_id(request, response)
    try:
        validate_config_input(conf, BACKENDS[backend].config_schema)
    except HTTPException as e:
        raise e
    session.config[backend] = conf
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)


@app.delete("/config/{backend}", description="Resets the configuration of the prompting method to its default.")
async def reset_config(request: Request, response: FastAPIResponse, backend: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    session.config[backend] = BACKENDS[backend].default_config()
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)

## Utility functions

async def handle_session_id(source: Union[Request, WebSocket], response: FastAPIResponse = None) -> SessionData:
    """
    Unified session handler for both HTTP requests and WebSocket connections.
    If no valid session ID is found, a new one is created and optionally set in the response cookie.
    """

    # Extract cookies from headers
    headers = Headers(scope=source.scope)
    cookies = headers.get("cookie")
    session_id = None

    # Extract session_id from cookies
    if cookies:
        cookie_dict = dict(cookie.split("=", 1) for cookie in cookies.split("; "))
        session_id = cookie_dict.get("session_id")

    # Session lock to avoid race conditions
    async with sessions_lock:
        max_age = 60 * 60 * 24 * 30  # 30 days
        # create Cookie (or just update max-age if already exists)
        session_id = create_or_refresh_session(session_id, max_age)

        # If it's an HTTP request and you want to set a cookie
        if response is not None:
            response.set_cookie("session_id", session_id, max_age=max_age)

        # Return the session data for the session ID
        return sessions[session_id]


def create_or_refresh_session(session_id, max_age=None):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        logger.info(f"Creating new Session {session_id}")
        sessions[session_id] = SessionData()
        sessions[session_id].opaca_client = OpacaClient()
    if max_age is not None:
        sessions[session_id].valid_until = time.time() + max_age
    return session_id


def handle_chat_id(session: SessionData, chat_id: str, create_if_missing: bool = False) -> Chat | None:
    chat = session.chats.get(chat_id, None)
    if chat is None and create_if_missing:
        chat = Chat(chat_id=chat_id)
        session.chats[chat_id] = chat
    elif chat is None and not create_if_missing:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def create_chat_name(chat: Chat | None, message: Message | None) -> None:
    if (chat is not None) and (message is not None) and not chat.name:
        chat.name = (f'{message.user_query[:32]}…'
            if len(message.user_query) > 32
            else message.user_query)


def update_chat_time(chat: Chat) -> None:
    chat.time_modified = datetime.now(tz=UTC)


async def store_message(chat: Chat, message: Message, result: Response):
    if message:
        chat.messages.extend([
            ChatMessage(role="user", content=message.user_query),
            ChatMessage(role="assistant", content=result.content)
        ])
        update_chat_time(chat)


async def cleanup_old_sessions(delay_seconds=3600):
    while True:
        logger.info("Checking for old Sessions...")
        now = time.time()
        async with sessions_lock:
            for session_id, session_data in list(sessions.items()):
                if session_data.valid_until < now:
                    logger.info(f"Removing old session {session_id}")
                    sessions.pop(session_id)
        await asyncio.sleep(delay_seconds)



# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
