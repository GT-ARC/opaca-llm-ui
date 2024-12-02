"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM clients that can be used,
and different routes for posting questions, updating the configuration, etc.
"""

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage

from .models import Url, Message, Response, ResponseData
from .toolllm import ToolLLMBackend
from .toolllama import LLamaBackend
from .restgpt import RestGptBackend
from .simple import SimpleOpenAIBackend, SimpleLlamaBackend
from .opaca_client import client
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
    "rest-gpt-llama3": RestGptBackend("llama3"),
    "rest-gpt-gpt-4o": RestGptBackend("gpt-4o"),
    "rest-gpt-gpt-4o-mini": RestGptBackend("gpt-4o-mini"),
    "simple-openai": SimpleOpenAIBackend(),
    "simple-llama": SimpleLlamaBackend(),
    "tool-llm-gpt-4o": ToolLLMBackend("gpt-4o"),
    "tool-llm-gpt-4o-mini": ToolLLMBackend("gpt-4o-mini"),
    "tool-llm-llama": LLamaBackend(),
    "itdz-knowledge": KnowledgeBackend(),
    "itdz-data": DataAnalysisBackend(),
}


sessions = {}


@app.get("/backends", description="Get list of available backends/LLM client IDs, to be used as parameter for other routes.")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(url: Url) -> int:
    return await client.connect(url.url, url.user, url.pwd)

@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform.")
async def actions() -> dict[str, list[str]]:
    return await client.get_actions()

@app.post("/{backend}/query", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, backend: str, message: Message) -> Response:
    session_id = get_session_id(request)
    response_data = await BACKENDS[backend].query(
        message.user_query,
        message.debug,
        message.api_key,
        sessions[session_id]["messages"],
        sessions[session_id].get(f'config-{backend}', await BACKENDS[backend].get_config()),
    )
    response = Response(response_data, session_id=session_id)
    return response

@app.get("/history", description="Get full message history of given LLM client since last reset.")
async def history(request: Request) -> Response:
    session_id = get_session_id(request)
    return Response(sessions[session_id]["messages"], session_id=session_id)

@app.post("/reset", description="Reset message history for the current session, restore/update system message if any.")
async def reset(request: Request) -> Response:
    session_id = get_session_id(request)
    sessions[session_id]["messages"].clear()
    return Response(session_id=session_id)

@app.post("/reset_all", description="Reset all message histories for")
async def reset_all():
    sessions.clear()

@app.get("/{backend}/config", description="Get current configuration of the given LLM client")
async def get_config(request: Request, backend: str) -> Response:
    session_id = get_session_id(request)
    sessions[session_id][f'config-{backend}'] = await BACKENDS[backend].get_config()
    return Response(sessions[session_id][f'config-{backend}'], session_id=session_id)

@app.put("/{backend}/config", description="Update configuration of the given LLM client.")
async def set_config(request: Request, backend: str, conf: dict) -> Response:
    session_id = get_session_id(request)
    sessions[session_id][f'config-{backend}'] = conf
    return Response(sessions[session_id][f'config-{backend}'], session_id=session_id)

def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        print(f'Created new session id: {session_id}')
        sessions[session_id] = {"messages": []}
    return session_id

# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
