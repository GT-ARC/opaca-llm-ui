from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from RestGPT import restgpt_routes
from OpenAI import openai_routes

"""
TODO
make same sort of interface-class/module for RestGPT
handle errors (backend not found, internal server error) as proper HTTP errors
test with javascript frontend (and throw out all the "backend" stuff there)
move get-opaca-agents and invoke-opaca-action to some common module?
make OPACA-URL configurable (simply as another route?)
"""


app = FastAPI()

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


BACKENDS = {
    "rest-gpt": restgpt_routes,
    "openai-test": openai_routes,
}


@app.get("/backends")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/{backend}/connect")
async def connect(backend: str, url: Url) -> bool:
    return await BACKENDS[backend].connect(url.url, url.user, url.pwd)

@app.post("/{backend}/query")
async def query(backend: str, message: Message) -> str:
    return await BACKENDS[backend].query(message.user_query)

@app.get("/{backend}/history")
async def history(backend: str) -> list:
    return await BACKENDS[backend].history()


@app.post("/{backend}/reset")
async def reset(backend: str):
    await BACKENDS[backend].reset()
