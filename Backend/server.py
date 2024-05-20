import json
import logging

from typing import Union, Dict, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from RestGPT import RestGPT, reduce_openapi_spec, ColorPrint
from OpenAI import openai_routes
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_community.utilities import Requests
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler

"""
TODO
make same sort of interface-class/module for RestGPT
handle errors (backend not found, internal server error) as proper HTTP errors
test with javascript frontend (and throw out all the "backend" stuff there)
move get-opaca-agents and invoke-opaca-action to some common module?
make OPACA-URL configurable (simply as another route?)
"""

logger = logging.getLogger()

logging.basicConfig(
    format="%(message)s",
    handlers=[logging.StreamHandler(ColorPrint())],
    level=logging.INFO
)


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
    prompt: str
    known_services: List


BACKENDS = {
    # "RestGPT": ???,
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


@app.post('/chat_test', response_model=Union[str, int, float, Dict, List])
async def test_call(message: Message):
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    llm = LlamaCpp(
        model_path="C:/Users/robst/PycharmProjects/llama.cpp/models/Meta-Llama-3-8B/ggml-model-f16.gguf",
        temperature=0.75,
        max_tokens=500,
        n_ctx=2048,
        top_p=1,
        callback_manager=callback_manager,
        verbose=True
    )

    action_spec = []
    for agent in message.known_services:
        for action in agent['actions']:
            action_spec.append(Action(name=action['name'], parameters=action['parameters'], result=action['result']))

    request_wrapper = Requests()
    rest_gpt = RestGPT(llm, action_spec=action_spec, requests_wrapper=request_wrapper,
                       simple_parser=False)

    logger.info(f'Query: {message.prompt}')

    return {'message': rest_gpt.invoke({"query": message.prompt})}
