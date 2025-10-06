import asyncio
import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Union, Optional
from fastapi import Request, Response, HTTPException
from pydantic import ValidationError
from starlette.websockets import WebSocket
from starlette.datastructures import Headers
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from urllib.parse import quote_plus

from .file_utils import delete_files_for_session
from .models import SessionData, Chat, QueryRequest, QueryResponse


DB_NAME: str = 'backend-data'
SESSIONS_COLLECTION: str = 'sessions'

logger = logging.getLogger(__name__)

# Simple dict to store session data in memory
# Is saved periodically to DB, and also on server shutdown
sessions_lock = asyncio.Lock()
sessions: Dict[str, SessionData] = {}


def __get_client(uri: Optional[str] = None) -> AsyncMongoClient:
    username = quote_plus(os.environ.get('MONGO_USERNAME', 'user'))
    password = quote_plus(os.environ.get('MONGO_PASSWORD', 'pass'))
    host = os.environ.get('MONGO_HOST', 'backend-db:27017')
    if uri is None:
        uri = f'mongodb://{username}:{password}@{host}'
    return AsyncMongoClient(uri)


def is_db_configured() -> bool:
    return os.environ.get('USE_MONGO_DB', '').lower() == 'true'


async def save_session(session: SessionData) -> None:
    """
    Saves a session to the database. Replace the existing one if session_id matches.
    """
    if not is_db_configured() or session is None:
        return
    bson = session.model_dump(mode='json', by_alias=True)
    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        try:
            await collection.replace_one({"_id": session.session_id}, bson, upsert=True)
        except Exception as e:
            logger.error(f'Failed to save session: {e}')


async def load_session(session_id: str) -> Optional[SessionData]:
    """
    Loads a session from the database. If it does not exist, return None.
    """
    if not is_db_configured() or not session_id:
        return None

    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        try:
            bson = await collection.find_one({"_id": session_id})
            if bson is None:
                return None
            return SessionData.model_validate(bson)
        except ValidationError as e:
            logger.error(f'Failed to load session {session_id}: {e}')
            await delete_session(session_id)
            return None
        except Exception as e:
            logger.error(f'Failed to load session {session_id}: {e}')
            return None


async def delete_session(session_id: str) -> None:
    """
    Deletes a session from the database.
    """
    if not is_db_configured() or not session_id:
        return

    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        try:
            await collection.delete_one({"_id": session_id})
        except Exception as e:
            logger.error(f'Failed to delete session {session_id}: {e}')


async def handle_session_id(source: Union[Request, WebSocket], response: Response = None) -> SessionData:
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
    session_id = await create_or_refresh_session(session_id, max_age)

    # If it's an HTTP request, and you want to set a cookie
    if response is not None:
        response.set_cookie("session_id", session_id, max_age=max_age)

    # Return the session data for the session ID
    return sessions[session_id]


async def create_or_refresh_session(session_id: Optional[str], max_age: int = 0) -> str:
    async with sessions_lock:
        session = (sessions.get(session_id, None)
            if session_id in sessions
            else await load_session(session_id))
        if session is None:
            session = create_new_session(session_id)
            logger.info(f"Created new session: {session.session_id}")
            session_id = session.session_id
            sessions[session_id] = session
        else:
            # if session was loaded from DB, save into memory
            logger.info(f'Session already exists: {session_id}')
            sessions[session_id] = session


        # update session expiration
        if max_age > 0:
            session.valid_until = time.time() + max_age

    return session_id


def create_new_session(session_id: Optional[str]) -> SessionData:
    session = SessionData()
    if session_id is not None and len(session_id) > 0:
        session.session_id = session_id
    return session


async def handle_chat_id(session: SessionData, chat_id: str, create_if_missing: bool = False) -> Chat | None:
    chat = session.chats.get(chat_id, None)
    if chat is None and create_if_missing:
        async with sessions_lock:
            chat = Chat(chat_id=chat_id)
            session.chats[chat_id] = chat
    elif chat is None and not create_if_missing:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


async def create_chat_name(chat: Chat | None, message: QueryRequest | None) -> None:
    if (chat is not None) and (message is not None) and not chat.name:
        chat.name = (f'{message.user_query[:32]}…'
            if len(message.user_query) > 32
            else message.user_query)


async def update_chat_time(chat: Chat) -> None:
    chat.time_modified = datetime.now(tz=timezone.utc)


async def store_message(chat: Chat, result: QueryResponse):
    chat.responses.append(result)
    await update_chat_time(chat)

async def delete_chat(session: SessionData, chat_id: str) -> bool:
    chat = session.chats.get(chat_id, None)
    if chat is None: return False
    del session.chats[chat_id]
    await delete_session(session.session_id)
    return True


async def store_sessions_in_db() -> None:
    async with sessions_lock:
        for session in sessions.values():
            await save_session(session)


async def cleanup_old_sessions(delay_seconds: int = 60 * 60 * 24) -> None:
    """
    Delete all expired sessions.

    :param delay_seconds: Number of seconds between cleanups. Default: 1 day.
    """
    while True:
        async with sessions_lock:
            logger.info("Checking for old Sessions...")
            now = time.time()
            for session_id, session in sessions.items():
                if session.valid_until < now:
                    logger.info(f"Removing old session {session_id}")
                    delete_files_for_session(session_id)
                    sessions.pop(session_id)
                    await delete_session(session_id)

        await asyncio.sleep(delay_seconds)


async def delete_all_sessions() -> None:
    async with sessions_lock:
        for session_id in sessions:
            sessions.pop(session_id)
            await delete_session(session_id)
