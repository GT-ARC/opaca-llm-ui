"""
FastAPI Server providing HTTP/REST routes to be used by the Frontend.
Provides a list of available LLM prompting methods that can be used,
and different routes for posting questions, updating the configuration, etc.
"""
import os
from typing import Dict, Any, List, Union, Optional
from http import HTTPStatus
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket
from starlette.datastructures import Headers

from .models import ConnectRequest, QueryRequest, QueryResponse, ConfigPayload, Chat, \
    SearchResult, get_supported_models, SessionData, OpacaException, PushMessage
from .simple import SimpleMethod
from .simple_tools import SimpleToolsMethod
from .toolllm import ToolLLMMethod
from .orchestrated import SelfOrchestratedMethod
from .internal_tools import InternalTools
from .file_utils import delete_file_from_all_clients, save_file_to_disk, create_path, delete_file_from_disk
from .session_manager import create_or_refresh_session, cleanup_task, on_shutdown, load_all_sessions, restore_scheduled_tasks

# Configure CORS settings
origins = os.getenv('CORS_WHITELIST', 'http://localhost:5173').split(";")


METHODS = {
    SimpleMethod.NAME: SimpleMethod,
    SimpleToolsMethod.NAME: SimpleToolsMethod,
    ToolLLMMethod.NAME: ToolLLMMethod,
    SelfOrchestratedMethod.NAME: SelfOrchestratedMethod,
}


logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # before start
    asyncio.create_task(cleanup_task())
    await load_all_sessions()
    await restore_scheduled_tasks(METHODS)

    try:
        # app running
        yield
    finally:
        # on shutdown
        await asyncio.wait_for(asyncio.shield(on_shutdown()), timeout=10)


app = FastAPI(
    title="SAGE Backend Services",
    summary="Provides services for interacting with the SAGE. Mainly to be used by the frontend, but can also be called directly.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# EXCEPTION HANDLING

@app.exception_handler(KeyError)
async def handle_key_error(request: Request, exc: KeyError):
    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Element not found: {exc}")

@app.exception_handler(ValueError)
async def handle_value_error(request: Request, exc: ValueError):
    raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=f"Illegal value: {exc}")

@app.exception_handler(TypeError)
async def handle_type_error(request: Request, exc: TypeError):
    raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=f"Unexpected type: {exc}")

@app.exception_handler(OpacaException)
async def handle_custom_error(request: Request, exc: OpacaException):
    raise HTTPException(status_code=exc.status_code, detail=f"{exc.user_message} (details: {exc.error_message})")


# 'GENERAL' ROUTES

@app.get("/methods", description="Get list of available LLM-prompting-methods, to be used as parameter for other routes.")
async def get_methods() -> list:
    return list(METHODS)


@app.get("/models", description="Get supported models, grouped by LLM server URL")
async def get_models() -> dict[str, list[str]]:
    return {
        url: models
        for url, _key, models in get_supported_models()
    }


@app.post("/connect", description="Connect to OPACA Runtime Platform. Returns the status code of the original request (to differentiate from errors resulting from this call itself).")
async def connect(request: Request, response: Response, connect: ConnectRequest) -> int:
    session = await handle_session_id(request, response)
    return await session.opaca_client.connect(connect.url, connect.user, connect.pwd)


@app.get("/connection", description="Get URL of currently connected OPACA Runtime Platform, if any, or null.")
async def get_connection(request: Request, response: Response) -> str | None:
    session = await handle_session_id(request, response)
    return session.opaca_client.url if session.opaca_client.connected else None


@app.post("/disconnect", description="Reset OPACA Runtime Connection.")
async def disconnect(request: Request, response: Response) -> Response:
    session = await handle_session_id(request, response)
    await session.opaca_client.disconnect()
    return Response(status_code=204)


@app.get("/actions", description="Get available actions on connected OPACA Runtime Platform, grouped by Agent, using the same format as the OPACA platform itself.")
async def get_actions(request: Request, response: Response) -> dict[str, List[Dict[str, Any]]]:
    session = await handle_session_id(request, response)
    return await session.opaca_client.get_actions_simple()


@app.post("/query/{method}", description="Send message to the given LLM method. Returns the final LLM response along with all intermediate messages and different metrics. This method does not include, nor is the message and response added to, any chat history.")
async def query_no_history(request: Request, response: Response, method: str, message: QueryRequest) -> QueryResponse:
    session = await handle_session_id(request, response)
    session.abort_sent = False
    try:
        return await METHODS[method](session, message.streaming).query(message.user_query, Chat(chat_id=''))
    except Exception as e:
        return QueryResponse.from_exception(message.user_query, e)


@app.post("/stop", description="Abort generation for every query of the current session.")
async def stop_query(request: Request, response: Response) -> None:
    session = await handle_session_id(request, response)
    session.abort_sent = True


### CHAT ROUTES

@app.get("/chats", description="Get available chats, just their names and IDs, but NOT the messages.")
async def get_chats(request: Request, response: Response) -> List[Chat]:
    session = await handle_session_id(request, response)
    chats = [
        Chat(chat_id=chat.chat_id, name=chat.name, time_created=chat.time_created, time_modified=chat.time_modified)
        for chat in session.chats.values()
    ]
    chats.sort(key=lambda chat: chat.time_modified, reverse=True)
    return chats


@app.get("/chats/{chat_id}", description="Get a chat's full history (including user queries, LLM responses, internal/intermediate messages, metrics, etc.).")
async def get_chat_history(request: Request, response: Response, chat_id: str) -> Chat:
    session = await handle_session_id(request, response)
    chat = session.get_or_create_chat(chat_id)
    return chat


@app.post("/chats/{chat_id}/query/{method}", description="Send message to the given LLM method; the history is stored in the backend and will be sent to the actual LLM along with the new message. Returns the final LLM response along with all intermediate messages and different metrics.")
async def query_chat(request: Request, response: Response, method: str, chat_id: str, message: QueryRequest) -> QueryResponse:
    session = await handle_session_id(request, response)
    chat = session.get_or_create_chat(chat_id, True)
    session.abort_sent = False
    result = None
    try:
        internal_tools = InternalTools(session, METHODS[method])
        result = await METHODS[method](session, message.streaming, internal_tools).query(message.user_query, chat)
    except Exception as e:
        result = QueryResponse.from_exception(message.user_query, e)
    finally:
        chat.store_interaction(result)
        return result


@app.put("/chats/{chat_id}", description="Update a chat's name.")
async def update_chat(request: Request, response: Response, chat_id: str, new_name: str) -> None:
    session = await handle_session_id(request, response)
    chat = session.get_or_create_chat(chat_id)
    chat.name = new_name
    chat.update_modified()


@app.delete("/chats/{chat_id}", description="Delete a single chat.")
async def delete_chat(request: Request, response: Response, chat_id: str) -> bool:
    session = await handle_session_id(request, response)
    return session.delete_chat(chat_id)


@app.delete("/chats", description="Delete all chats of the current session.")
async def delete_all_chats(request: Request, response: Response) -> bool:
    session = await handle_session_id(request, response)
    session.chats.clear()
    return True


@app.post("/chats/search", description="Search through all chats for a given query.")
async def search_chats(request: Request, response: Response, query: str) -> Dict[str, List[SearchResult]]:
    def make_excerpt(text: str, query: str, index: int, buffer_length: int = 30) -> str:
        start = max(0, index - buffer_length)
        stop = min(len(text), index + len(query) + buffer_length)
        excerpt = message.content[start:stop]
        if start > 0:
            excerpt = f'...{excerpt}'
        if stop < len(text):
            excerpt = f'{excerpt}...'
        return excerpt

    if len(query) < 1: return {}
    session = await handle_session_id(request, response)
    results = {}
    query = query.lower()
    for chat in session.chats.values():
        for message_id, message in enumerate(chat.messages):
            index = -1
            while (index := message.content.lower().find(query, index+1)) >= 0:
                if chat.chat_id not in results:
                    results[chat.chat_id] = []
                results[chat.chat_id].append(SearchResult(
                    chat_id=chat.chat_id,
                    chat_name=chat.name,
                    message_id=message_id,
                    excerpt=make_excerpt(message.content, query, index),
                ))

    return results


@app.post("/chats/{chat_id}/append", description="Append a single push message to a chat")
async def append(chat_id: str, push_message: PushMessage, request: Request, response: Response) -> None:
    session = await handle_session_id(request, response)
    chat = session.get_or_create_chat(chat_id, True)
    chat.store_interaction(push_message)


## CONFIG ROUTES

@app.get("/config/{method}", description="Get current configuration of the given prompting method.")
async def get_config(request: Request, response: Response, method: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    return ConfigPayload(config_values=session.get_config(METHODS[method]), config_schema=METHODS[method].config_schema())


@app.put("/config/{method}", description="Update configuration of the given prompting method.")
async def set_config(request: Request, response: Response, method: str, config: dict) -> ConfigPayload:
    session = await handle_session_id(request, response)
    try:
        session.config[method] = METHODS[method].CONFIG.model_validate(config)
    except Exception as e:
        raise e  # converted to HTTP Exception by FastAPI
    return ConfigPayload(config_values=session.config[method], config_schema=METHODS[method].config_schema())


@app.delete("/config/{method}", description="Resets the configuration of the prompting method to its default.")
async def reset_config(request: Request, response: Response, method: str) -> ConfigPayload:
    session = await handle_session_id(request, response)
    session.config[method] = METHODS[method].CONFIG()
    return ConfigPayload(config_values=session.config[method], config_schema=METHODS[method].config_schema())

## FILE ROUTES

@app.get("/files", description="Get a list of all uploaded files.")
async def get_files(request: Request, response: Response) -> dict:
    session = await handle_session_id(request, response)
    return session.uploaded_files


@app.post("/files", description="Upload a file to the backend, to be sent to the LLM for consideration "
                                "with the next user queries. Currently only supports PDF.")
async def upload_files(request: Request, response: Response, files: List[UploadFile]):
    session = await handle_session_id(request, response)
    uploaded = []
    for file in files:
        try:
            filedata = await save_file_to_disk(file, session.session_id)
            session.uploaded_files[filedata.file_id] = filedata
            uploaded.append(filedata)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file {file.filename}: {str(e)}"
            )

    return {"uploaded_files": uploaded}


@app.delete("/files/{file_id}", description="Delete an uploaded file.")
async def delete_file(request: Request, response: Response, file_id: str) -> bool:
    session = await handle_session_id(request, response)
    files = session.uploaded_files

    if file_id in files:
        delete_file_from_disk(session.session_id, file_id)
        result = await delete_file_from_all_clients(session, file_id)
        return result

    return False


@app.patch("/files/{file_id}", description="Mark a file as suspended or unsuspended.")
async def update_file(request: Request, response: Response, file_id: str, suspend: bool) -> bool:
    session = await handle_session_id(request, response)
    files = session.uploaded_files

    if file_id in files:
        file = files[file_id]
        file.suspended = suspend
        return True

    return False


@app.get("/files/{file_id}/view", description="Serve a previously uploaded file for preview.")
async def view_file(request: Request, response: Response, file_id: str):
    session = await handle_session_id(request, response)
    files = session.uploaded_files

    if file_id not in files:
        raise HTTPException(status_code=404, detail="File not found")

    file = files[file_id]
    file_path = create_path(session.session_id, file_id)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    # Serve the file with inline disposition so browsers render PDFs/images
    return FileResponse(
        path=file_path,
        media_type=file.content_type,
        filename=file.file_name,
        headers={"Content-Disposition": f'inline; filename="{file.file_name}"'}
    )


## BOOKMARK ROUTES

@app.get("/bookmarks")
async def get_bookmarks(request: Request) -> list:
    session = await handle_session_id(request)
    return session.bookmarks


@app.post("/bookmarks")
async def save_bookmarks(request: Request) -> None:
    session = await handle_session_id(request)
    new_bookmarks = await request.json()
    session.bookmarks = new_bookmarks


# WEBSOCKET CONNECTION (permanently opened)

@app.websocket("/ws")
async def open_websocket(websocket: WebSocket):
    await websocket.accept()
    session = await handle_session_id(websocket)
    session._websocket = websocket
    session._ws_msg_queue = asyncio.Queue()
    await session.websocket_send_pending()
    try:
        while True:
            logger.debug("websocket waiting...")
            # messages coming from the websocket are received here and put into an async queue
            # so any exceptions (like websocket closing) can be handled here without losing messages
            response = await websocket.receive_json()
            await session._ws_msg_queue.put(response)
    except Exception as e:
        pass  # this is normal when e.g. the browser is closed
    finally:
        session._websocket = None


## HELPER FUNCTIONS

async def handle_session_id(source: Union[Request, WebSocket], response: Optional[Response] = None) -> SessionData:
    """
    Unified session handler for both HTTP requests and WebSocket connections.
    If no valid session ID is found, a new one is created and optionally set in the response cookie.
    """

    # Extract cookies from headers
    headers = Headers(scope=source.scope)
    cookies = headers.get("cookie")
    session_id = None

    # Extract session_id from cookies
    if cookies:
        cookie_dict = dict(cookie.split("=", 1) for cookie in cookies.split("; "))
        session_id = cookie_dict.get("session_id", None)

    max_age = 60 * 60 * 24 * 30  # 30 days
    # create Cookie (or just update max-age if already exists)
    session = await create_or_refresh_session(session_id, max_age)

    # If it's an HTTP request, and you want to set a cookie
    if response is not None:
        response.set_cookie("session_id", session.session_id, max_age=max_age)

    # Return the session data for the session ID
    return session


# run as `python3 -m Backend.server`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
