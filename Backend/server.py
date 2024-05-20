import json
import logging

from typing import Union, Dict, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from RestGPT import RestGPT, reduce_openapi_spec, ColorPrint
from openai import OpenAI
from langchain_community.llms.llamacpp import LlamaCpp
from langchain_community.utilities import Requests
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler


logger = logging.getLogger()

logging.basicConfig(
    format="%(message)s",
    handlers=[logging.StreamHandler(ColorPrint())],
    level=logging.INFO
)


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
    prompt: str
    known_services: List


class Action(BaseModel):
    name: str
    parameters: Dict
    result: Dict


@app.post('/wapi/chat')
async def chat(message: Message):
    prompt = message.prompt
    try:
        if prompt is None:
            raise HTTPException(status_code=400, detail='Invalid prompt')

        client = OpenAI(api_key='sk-proj-W0P92cfYwDHqFhBSvqbuT3BlbkFJBBwhd09LGW0u1RSwPXVL')

        completion = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=message.prompt,
        )

        print(f'Complete response from OpenAI: {completion}')
        print(f'Message from OpenAI: {completion.choices[0].message}')
        prompt.append(completion.choices[0].message)

        return {'success': True, 'messages': prompt}
    except Exception as e:
        return {'success': False, 'messages': str(e)}


@app.post('/chat_test', response_model=Union[str, int, float, Dict, List])
async def test_call(message: Message):
    print("Got Here")
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    llm = LlamaCpp(
        model_path='C:/Users/robst/Meta-Llama-3-8B/ggml-model-f16.gguf',
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
