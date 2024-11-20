"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available "backends", or LLM clients that can be used,
and different routes for posting questions, updating the configuration, etc.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import Url, Message, Response
from .toolllm import ToolLLMBackend
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
    "rest-gpt-llama3": RestGptBackend("llama3"),
    "rest-gpt-gpt-4o": RestGptBackend("gpt-4o"),
    "rest-gpt-gpt-4o-mini": RestGptBackend("gpt-4o-mini"),
    "simple-openai": SimpleOpenAIBackend(),
    "simple-llama": SimpleLlamaBackend(),
    "tool-llm-gpt-4o": ToolLLMBackend("gpt-4o"),
    "tool-llm-gpt-4o-mini": ToolLLMBackend("gpt-4o-mini"),
    "itdz-knowledge": KnowledgeBackend(),
    "itdz-data": DataAnalysisBackend(),
}


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
async def query(backend: str, message: Message) -> Response:
    return await BACKENDS[backend].query(message.user_query, message.debug, message.api_key)

@app.get("/{backend}/history", description="Get full message history of given LLM client since last reset.")
async def history(backend: str) -> list:
    return await BACKENDS[backend].history()

@app.post("/{backend}/reset", description="Reset message history for the given LLM client, restore/update system message if any.")
async def reset(backend: str):
    await BACKENDS[backend].reset()

@app.get("/{backend}/config", description="Get current configuration of the given LLM client")
async def get_config(backend: str) -> dict:
    return await BACKENDS[backend].get_config()

@app.put("/{backend}/config", description="Update configuration of the given LLM client.")
async def set_config(backend: str, conf: dict) -> dict:
    await BACKENDS[backend].set_config(conf)
    return await BACKENDS[backend].get_config()


# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
