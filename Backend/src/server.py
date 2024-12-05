"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM clients that can be used,
and different routes for posting questions, updating the configuration, etc.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi import Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware

from .models import Url, Message, Response, SessionData
from .toolllm import ToolLLMBackend
from .toolllama import LLamaBackend
from .restgpt import RestGptBackend
from .simple import SimpleOpenAIBackend, SimpleLlamaBackend
from .opaca_client import OpacaClient
from .proxy import KnowledgeBackend, DataAnalysisBackend


app = FastAPI(
    title="OPACA LLM Backend Services",
    summary="Provides services for interacting with the OPACA LLM. Mainly to be used by the frontend, but can also be called directly."
)

# Configure CORS settings
origins = [
    "http://localhost",
    "http://localhost:5173",  # Assuming Vue app is running on this port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BACKENDS = {
    "rest-gpt-openai": RestGptBackend(use_llama=False),
    "rest-gpt-llama": RestGptBackend(use_llama=True),
    "simple-openai": SimpleOpenAIBackend(),
    "simple-llama": SimpleLlamaBackend(),
    "tool-llm-openai": ToolLLMBackend(),
    "tool-llm-llama": LLamaBackend(),
    # special backends
    "itdz-knowledge": KnowledgeBackend(),
    "itdz-data": DataAnalysisBackend(),
}


# Simple dict to store session data
# Keep in mind: The session data is only reset upon restarting the application
sessions = {}


@app.get("/backends", description="Get list of available backends/LLM client IDs, to be used as parameter for other routes.")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: FastAPIResponse, url: Url) -> int:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    sessions[session_id].client = OpacaClient()
    return await sessions[session_id].client.connect(url.url, url.user, url.pwd)

@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform.")
async def actions(request: Request, response: FastAPIResponse) -> dict[str, list[str]]:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    return await sessions[session_id].client.get_actions()

@app.post("/{backend}/query", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, response: FastAPIResponse, backend: str, message: Message) -> Response:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    return await BACKENDS[backend].query(
        message.user_query,
        message.debug,
        message.api_key,
        sessions[session_id]
    )

@app.get("/history", description="Get full message history of given LLM client since last reset.")
async def history(request: Request, response: FastAPIResponse) -> list:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    return sessions[session_id].messages

@app.post("/reset", description="Reset message history for the current session.")
async def reset(request: Request, response: FastAPIResponse) -> None:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    sessions[session_id].messages.clear()

@app.post("/reset_all", description="Reset all sessions")
async def reset_all():
    sessions.clear()

@app.get("/{backend}/config", description="Get current configuration of the given LLM client.")
async def get_config(request: Request, response: FastAPIResponse, backend: str) -> dict:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    sessions[session_id].config[backend] = sessions[session_id].config.get(backend, await BACKENDS[backend].get_config())
    return sessions[session_id].config[backend]

@app.put("/{backend}/config", description="Update configuration of the given LLM client.")
async def set_config(request: Request, response: FastAPIResponse, backend: str, conf: dict) -> dict:
    session_id = handle_session_id(request)
    response.set_cookie("session_id", session_id)
    sessions[session_id].config[backend] = conf
    return sessions[session_id].config[backend]

def handle_session_id(request: Request):
    """
    Gets the session id from the request object. If no session id was found or the id is unknown, creates a new
    session id and adds an empty list of messages to that session id.
    """
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = SessionData()
    return session_id

# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
