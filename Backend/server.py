import json

from typing import Union, Dict, List
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from OpenAI import openai_routes

'''
from Backend.RestGPT import RestGPT
from Backend.RestGPT import reduce_openapi_spec
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_community.utilities import Requests
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
'''

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

class Message(BaseModel):
    user_query: str


BACKENDS = {
    # "RestGPT": ???,
    "openai-test": openai_routes,
}


@app.get("/backends")
async def get_backends() -> list:
    return list(BACKENDS)

@app.post("/{backend}/connect")
async def query(backend: str, url: Url) -> bool:
    return await BACKENDS[backend].connect(url.url)

@app.post("/{backend}/query")
async def query(backend: str, message: Message) -> str:
    return await BACKENDS[backend].query(message.user_query)

@app.get("/{backend}/history")
async def history(backend: str) -> list:
    return await BACKENDS[backend].history()


@app.post("/{backend}/reset")
async def query(backend: str) -> str:
    await BACKENDS[backend].reset()


'''
@app.post('/chat_test', response_model=Union[str, int, float, Dict, List])
async def test_call(message: Message):
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    llm = LlamaCpp(
        model_path="C:/Users/robst/PycharmProjects/llama.cpp/models/Meta-Llama-3-8B/ggml-model-f16.gguf",
        temperature=0.75,
        max_tokens=10,
        top_p=1,
        callback_manager=callback_manager,
        verbose=True
    )
    with open("C:/Users/robst/IdeaProjects/openai-test/Backend/specs/tmdb_oas.json") as f:
        raw_tmdb_api_spec = json.load(f)
    """
    api_spec = reduce_openapi_spec(raw_tmdb_api_spec, only_required=False)
    request_wrapper = Requests()
    rest_gpt = RestGPT(llm, api_spec=api_spec, scenario='TMDB', requests_wrapper=request_wrapper,
                       simple_parser=False)
    """
    return {'message': llm.invoke(message.user_query)}
'''


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
