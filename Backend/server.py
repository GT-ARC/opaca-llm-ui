import json

from typing import Union, Dict, List
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Backend.RestGPT import RestGPT
from Backend.RestGPT import reduce_openapi_spec
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_community.utilities import Requests
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler


app = FastAPI()

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


class Message(BaseModel):
    user_query: str


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
