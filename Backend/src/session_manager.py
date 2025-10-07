import asyncio
import os
import time
import logging
from datetime import datetime, timezone
from logging import Logger
from typing import Dict, Union, Optional, Iterator, List
from fastapi import Request, Response, HTTPException
from pydantic import ValidationError
from pymongo import ASCENDING
from starlette.websockets import WebSocket
from starlette.datastructures import Headers
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from .file_utils import delete_files_for_session
from .models import SessionData, Chat, QueryRequest, QueryResponse


logger: Logger = logging.getLogger(__name__)

DB_NAME: str = 'backend-data'
SESSIONS_COLLECTION: str = 'sessions'

# Simple dict to store session data in memory
# Is saved periodically to DB, and also on server shutdown
sessions_lock: asyncio.Lock = asyncio.Lock()
sessions: Dict[str, SessionData] = {}


def __get_client(uri: Optional[str] = None) -> AsyncMongoClient:
    if uri is None:
        uri = os.environ.get('MONGODB_URI', None)
    logger.info(f'Connecting to {uri}')
    return AsyncMongoClient(uri)


# client for communicating with the db
__client: AsyncMongoClient = __get_client()


def is_db_configured() -> bool:
    return len(os.environ.get('MONGODB_URI', '').strip()) > 0


async def save_session(session: SessionData) -> None:
    """
    Saves a session to the database. Replace the existing one if session_id matches.
    """
    if not is_db_configured() or session is None:
        return
    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    try:
        logger.debug(f'Storing session {session.session_id} in DB.')
        bson = session.model_dump(mode='json', by_alias=True)
        await collection.replace_one({'_id': session.session_id}, bson, upsert=True)
    except Exception as e:
        logger.error(f'Failed to save session: {e}')


async def load_session(session_id: str) -> Optional[SessionData]:
    """
    Loads a session from the database. If it does not exist, return None.
    """
    if not is_db_configured() or not session_id:
        return None
    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    try:
        bson = await collection.find_one({'_id': session_id})
        if bson is None:
            return None
        logger.debug(f'Loaded data for session {session_id} from DB.')
        return SessionData.model_validate(bson)
    except ValidationError as e:
        logger.error(f'Invalid data for session {session_id}: {e}')
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
    logger.debug(f'Deleting data for session {session_id} from DB.')
    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    try:
        await collection.delete_one({"_id": session_id})
    except Exception as e:
        logger.error(f'Failed to delete session {session_id}: {e}')


async def find_session_ids() -> List[str]:
    if not is_db_configured(): return []
    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    cursor = collection.find({}, {'_id': 1})
    return [doc['_id'] async for doc in cursor]


async def load_all_sessions() -> None:
    """
    Load all session data from DB into memory.
    """
    if not is_db_configured(): return
    session_ids = await find_session_ids()
    logger.info(f'Loaded {len(session_ids)} sessions from DB.')
    for session_id in session_ids:
        session = await load_session(session_id)
        if session is not None and is_session_valid(session, do_delete=True):
            sessions[session_id] = session


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
            # if session is valid and was loaded from DB, save into memory
            sessions[session_id] = session

        # update session expiration
        if max_age > 0:
            session.valid_until = time.time() + max_age

    return session_id


def create_new_session(session_id: Optional[str] = None) -> SessionData:
    session = SessionData()
    if session_id is not None and len(session_id) > 0:
        session.session_id = session_id
    return session


async def handle_chat_id(session: SessionData, chat_id: str, create_if_missing: bool = False) -> Chat | None:
    chat = session.chats.get(chat_id, None)
    if chat is None and create_if_missing:
        chat = Chat(chat_id=chat_id)
        session.chats[chat_id] = chat
    elif chat is None and not create_if_missing:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


def create_chat_name(chat: Chat | None, message: QueryRequest | None) -> None:
    if (chat is not None) and (message is not None) and not chat.name:
        chat.name = (f'{message.user_query[:32]}…'
            if len(message.user_query) > 32
            else message.user_query)


def update_chat_time(chat: Chat) -> None:
    chat.time_modified = datetime.now(tz=timezone.utc)


async def store_message(chat: Chat, result: QueryResponse):
    chat.responses.append(result)
    update_chat_time(chat)


def delete_chat(session: SessionData, chat_id: str) -> bool:
    chat = session.chats.get(chat_id, None)
    if chat is None: return False
    del session.chats[chat_id]
    return True


async def store_sessions_in_db() -> None:
    if len(sessions) == 0: return
    logger.info(f'Storing data for {len(sessions)} sessions in database...')
    async with sessions_lock:
        for session in sessions.values():
            await save_session(session)


async def cleanup_old_sessions() -> None:
    """
    Delete all expired sessions.
    """
    logger.info("Cleaning out expired sessions...")
    for session_id, session in sessions.items():
        await is_session_valid(session, do_delete=True)


async def is_session_valid(session: SessionData, do_delete: bool = True) -> bool:
    """
    Check if the session is valid, e.g. exists, not expired, etc.

    :param session: The session to check.
    :param do_delete: If True, delete the session from the database if it's not valid.
    """
    if session is None: return False
    if session.valid_until >= time.time(): return True
    async with sessions_lock:
        logger.warning(f'Session {session.session_id} has expired.')
        if do_delete:
            if session.session_id in sessions:
                del sessions[session.session_id]
            delete_files_for_session(session.session_id)
            await delete_session(session.session_id)
    return True


async def delete_all_sessions() -> None:
    logger.warning("Deleting all sessions...")
    async with sessions_lock:
        for session_id in sessions:
            await delete_session(session_id)
        sessions.clear()


async def cleanup_task(delay_seconds: int = 60 * 60 * 24) -> None:
    """
    Cleanup old session and files, and save the current sessions to DB
    in a configurable interval.

    :param delay_seconds: Number of seconds after which this task repeats. Defaults to 86400s (1 day).
    """
    while True:
        await cleanup_old_sessions()
        await store_sessions_in_db()
        await asyncio.sleep(delay_seconds)


async def on_shutdown():
    if __client is not None:
        await __client.close()
