"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM clients that can be used,
and different routes for posting questions, updating the configuration, etc.
"""
import os
import uuid
from typing import List, Dict, Any
import asyncio

from fastapi import FastAPI, Request, HTTPException
from fastapi import Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import Headers
from starlette.websockets import WebSocket

from .utils import validate_config_input, exception_to_result
from .models import ConnectInfo, Message, Response, SessionData, ConfigPayload, ChatMessage, OpacaException
from .toolllm import *
from .simple import SimpleBackend
from .simple_tools import SimpleToolsBackend
from .opaca_client import OpacaClient
from .orchestrated import SelfOrchestratedBackend


app = FastAPI(
    title="OPACA LLM Backend Services",
    summary="Provides services for interacting with the OPACA LLM. Mainly to be used by the frontend, but can also be called directly."
)

# Configure CORS settings
origins = [
    f"{os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')}",
    f"{os.getenv('SMARTSPACE_BASE_URL', 'http://localhost:5174')}",
]

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
sessions = {}



@app.get("/backends", description="Get list of available backends/LLM client IDs, to be used as parameter for other routes.")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: FastAPIResponse, url: ConnectInfo) -> int:
    session = await handle_session_id(request, response)
    return await session.opaca_client.connect(url.url, url.user, url.pwd)

@app.post("/disconnect", description="Reset OPACA Runtime Connection.")
async def disconnect(request: Request, response: FastAPIResponse) -> None:
    session = await handle_session_id(request, response)
    await session.opaca_client.disconnect()
    return FastAPIResponse(status_code=204)

@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform.")
async def actions(request: Request, response: FastAPIResponse) -> dict[str, List[Dict[str, Any]]]:
    session = await handle_session_id(request, response)
    return await session.opaca_client.get_actions_simple()

@app.post("/{backend}/query", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, response: FastAPIResponse, backend: str, message: Message) -> Response:
    session = await handle_session_id(request, response)
    session.abort_sent = False
    try:
        await BACKENDS[backend].init_models(session)
        result = await BACKENDS[backend].query(message.user_query, session)
        if message.store_in_history:
            session.messages.extend([
                ChatMessage(role="user", content=message.user_query),
                ChatMessage(role="assistant", content=result.content)
            ])
        return result
    except Exception as e:
        return exception_to_result(message.user_query, e)

@app.websocket("/{backend}/query_stream")
async def query_stream(websocket: WebSocket, backend: str):
    await websocket.accept()
    session = await handle_session_id_for_websocket(websocket)
    session.abort_sent = False
    try:
        data = await websocket.receive_json()
        message = Message(**data)
        await BACKENDS[backend].init_models(session)
        result = await BACKENDS[backend].query_stream(message.user_query, session, websocket)
        if message.store_in_history:
            session.messages.extend([
                ChatMessage(role="user", content=message.user_query),
                ChatMessage(role="assistant", content=result.content)
            ])
        await websocket.send_json(result.model_dump_json())
    except Exception as e:
        result = exception_to_result(message.user_query, e)
        await websocket.send_json(result.model_dump_json())
    finally:
        await websocket.close()

@app.post("/stop", description="Abort generation for last query.")
async def history(request: Request, response: FastAPIResponse) -> None:
    session = await handle_session_id(request, response)
    session.abort_sent = True

@app.get("/history", description="Get full message history of given LLM client since last reset.")
async def history(request: Request, response: FastAPIResponse) -> list:
    session = await handle_session_id(request, response)
    return session.messages

@app.post("/reset", description="Reset message history for the current session.")
async def reset(request: Request, response: FastAPIResponse) -> FastAPIResponse:
    session = await handle_session_id(request, response)
    session.messages.clear()
    return FastAPIResponse(status_code=204)

@app.post("/reset_all", description="Reset all sessions")
async def reset_all():
    async with sessions_lock:
        sessions.clear()

@app.get("/{backend}/config", description="Get current configuration of the given LLM client.")
async def get_config(request: Request, response: FastAPIResponse, backend: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    if backend not in session.config:
        session.config[backend] = BACKENDS[backend].default_config()
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)

@app.put("/{backend}/config", description="Update configuration of the given LLM client.")
async def set_config(request: Request, response: FastAPIResponse, backend: str, conf: dict) -> ConfigPayload:
    session = await handle_session_id(request, response)
    try:
        validate_config_input(conf, BACKENDS[backend].config_schema)
    except HTTPException as e:
        raise e
    session.config[backend] = conf
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)

@app.post("/{backend}/config/reset", description="Resets the configuration of the LLM client to its default.")
async def reset_config(request: Request, response: FastAPIResponse, backend: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    session.config[backend] = BACKENDS[backend].default_config()
    return ConfigPayload(value=session.config[backend], config_schema=BACKENDS[backend].config_schema)

async def handle_session_id(request: Request, response: FastAPIResponse) -> SessionData:
    """
    Gets the session id from the request object. If no session id was found or the id is unknown, creates a new
    session id and adds an empty list of messages to that session id. Also sets the same session-id in the
    response and return the SessionData associated with that session-id.
    """
    session_id = request.cookies.get("session_id")
    async with sessions_lock:
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = SessionData()
            sessions[session_id].opaca_client = OpacaClient()
        response.set_cookie("session_id", session_id)
        return sessions[session_id]

async def handle_session_id_for_websocket(websocket: WebSocket) -> SessionData:
    """
    Gets the session id from a websocket and returns the corresponding session data. If no session id was found
    or the id is unknown, creates a new session id and adds an empty list of messages to that session id.
    """
    # Extract cookies from headers
    headers = Headers(scope=websocket.scope)
    cookies = headers.get("cookie")
    session_id = None

    if cookies:
        cookie_dict = {cookie.split("=")[0]: cookie.split("=")[1] for cookie in cookies.split("; ")}
        session_id = cookie_dict.get("session_id")

    async with sessions_lock:
        # If session ID is not found or invalid, create a new one
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = SessionData()
            sessions[session_id].opaca_client = OpacaClient()

        # Return the session data for the session ID
        return sessions[session_id]

# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
