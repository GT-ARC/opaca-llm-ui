from typing import Dict

from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .RestGPT.restgpt_routes import RestGptBackend
from .Simple.simple_routes import SimpleOpenAIBackend, SimpleLlamaBackend
from .opaca_proxy import proxy

"""
TODO
make same sort of interface-class/module for RestGPT
handle errors (backend not found, internal server error) as proper HTTP errors
test with javascript frontend (and throw out all the "backend" stuff there)
move get-opaca-agents and invoke-opaca-action to some common module?
make OPACA-URL configurable (simply as another route?)
"""

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


class Url(BaseModel):
    url: str
    user: str | None
    pwd: str | None


class Message(BaseModel):
    user_query: str
    debug: bool
    api_key: str


BACKENDS = {
    "rest-gpt-llama3": RestGptBackend("llama3"),
    "rest-gpt-gpt-4o": RestGptBackend("gpt-4o"),
    "rest-gpt-gpt-3.5-turbo": RestGptBackend("gpt-3.5-turbo"),
    "simple-openai": SimpleOpenAIBackend(),
    "simple-llama": SimpleLlamaBackend(),
}


@app.get("/backends")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/connect")
async def connect(url: Url) -> bool:
    return await proxy.connect(url.url, url.user, url.pwd)

@app.post("/{backend}/query")
async def query(backend: str, message: Message) -> Dict:
    return await BACKENDS[backend].query(message.user_query, message.debug, message.api_key)

@app.get("/{backend}/history")
async def history(backend: str) -> list:
    return await BACKENDS[backend].history()

@app.post("/{backend}/reset")
async def reset(backend: str):
    await BACKENDS[backend].reset()

@app.get("/{backend}/config")
async def get_config(backend: str) -> dict:
    return await BACKENDS[backend].get_config()

@app.put("/{backend}/config")
async def set_config(backend: str, conf: dict) -> dict:
    await BACKENDS[backend].set_config(conf)
    return await BACKENDS[backend].get_config()


# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
