"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM clients that can be used,
and different routes for posting questions, updating the configuration, etc.
"""
import asyncio
import uuid

from fastapi import FastAPI, Request
from fastapi import Response as FastAPIResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .models import Url, Message, Response, SessionData
from .toolllm import *
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
    "*",
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
    RestGptBackend.NAME_OPENAI: RestGptBackend(use_llama=False),
    RestGptBackend.NAME_LLAMA: RestGptBackend(use_llama=True),
    SimpleOpenAIBackend.NAME: SimpleOpenAIBackend(),
    SimpleLlamaBackend.NAME: SimpleLlamaBackend(),
    # special backends
    KnowledgeBackend.NAME: KnowledgeBackend(),
    DataAnalysisBackend.NAME: DataAnalysisBackend(),
}

BACKENDS |= {method: ToolLLMBackend(method) for method in ToolMethodRegistry.registry.keys()}


# Simple dict to store session data
# Keep in mind: The session data is only reset upon restarting the application
sessions = {}

data = None


@app.get("/backends", description="Get list of available backends/LLM client IDs, to be used as parameter for other routes.")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: FastAPIResponse, url: Url) -> int:
    session = handle_session_id(request, response)
    session.client = OpacaClient()
    return await session.client.connect(url.url, url.user, url.pwd)

@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform.")
async def actions(request: Request, response: FastAPIResponse) -> dict[str, list[str]]:
    session = handle_session_id(request, response)
    return await session.client.get_actions()

@app.post("/{backend}/query", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, response: FastAPIResponse, backend: str, message: Message) -> Response:
    session = handle_session_id(request, response)
    return await BACKENDS[backend].query(message.user_query, session)

async def stream_example():
    response = Response(content=f'')
    for i in range(0, 10):
        response.content += f"Message {i}\n"
        yield f'data: {response.model_dump_json()}\n\n'
        await asyncio.sleep(1)

@app.post("/{backend}/query_start_stream", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, response: FastAPIResponse, backend: str, message: Message) -> Response:
    print(f'in Start stream')
    session = handle_session_id(request, response)
    return Response(content="Started generation")

@app.get("/{backend}/query_stream_result", description="Send message to the given LLM backend; the history is stored in the backend and will be sent to the actual LLM along with the new message.")
async def query(request: Request, response: StreamingResponse) -> StreamingResponse:
    print(f'in stream result with request: {request}')
    session = handle_session_id(request, response)
    return StreamingResponse(stream_example(), media_type="text/event-stream")

@app.get("/history", description="Get full message history of given LLM client since last reset.")
async def history(request: Request, response: FastAPIResponse) -> list:
    session = handle_session_id(request, response)
    return session.messages

@app.post("/reset", description="Reset message history for the current session.")
async def reset(request: Request, response: FastAPIResponse) -> None:
    session = handle_session_id(request, response)
    session.messages.clear()

@app.post("/reset_all", description="Reset all sessions")
async def reset_all():
    sessions.clear()

@app.get("/{backend}/config", description="Get current configuration of the given LLM client.")
async def get_config(request: Request, response: FastAPIResponse, backend: str) -> dict:
    session = handle_session_id(request, response)
    if backend not in session.config:
        session.config[backend] = BACKENDS[backend].default_config
    return session.config[backend]

@app.put("/{backend}/config", description="Update configuration of the given LLM client.")
async def set_config(request: Request, response: FastAPIResponse, backend: str, conf: dict) -> dict:
    session = handle_session_id(request, response)
    session.config[backend] = conf
    return session.config[backend]

@app.post("/{backend}/config/reset", description="Resets the configuration of the LLM client to its default.")
async def reset_config(request: Request, response: FastAPIResponse, backend: str) -> dict:
    session = handle_session_id(request, response)
    session.config[backend] = await BACKENDS[backend].get_config()
    return session.config[backend]

def handle_session_id(request: Request, response: FastAPIResponse | StreamingResponse) -> SessionData:
    """
    Gets the session id from the request object. If no session id was found or the id is unknown, creates a new
    session id and adds an empty list of messages to that session id. Also sets the same session-id in the 
    response and return the SessionData associated with that session-id.
    """
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = SessionData()
    response.set_cookie("session_id", session_id)
    return sessions[session_id]

# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
