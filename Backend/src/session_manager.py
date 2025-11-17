import asyncio
import os
import time
import logging
from logging import Logger
from typing import Dict, Optional, List
from pydantic import ValidationError
from pymongo.asynchronous.mongo_client import AsyncMongoClient

from .file_utils import delete_all_files_from_disk
from .internal_tools import InternalTools
from .models import SessionData


logger: Logger = logging.getLogger(__name__)

DB_NAME: str = 'backend-data'
SESSIONS_COLLECTION: str = 'sessions'

# Simple dict to store session data in memory
# Is saved periodically to DB, and also on server shutdown
sessions_lock: asyncio.Lock = asyncio.Lock()
sessions: Dict[str, SessionData] = {}


class SessionDbClient:

    def __init__(self, uri: Optional[str] = None):
        logger.info(f'Connecting to {uri}')
        self.client = AsyncMongoClient(uri) if uri else None


    def is_db_configured(self) -> bool:
        return self.client is not None


    async def save_session(self, session: SessionData) -> None:
        """
        Saves a session to the database. Replace the existing one if session_id matches.
        """
        if not self.is_db_configured() or session is None:
            return
        collection = self.client[DB_NAME][SESSIONS_COLLECTION]
        try:
            logger.debug(f'Storing session {session.session_id} in DB.')
            bson = session.model_dump(mode='json', by_alias=True)
            await collection.replace_one({'_id': session.session_id}, bson, upsert=True)
        except Exception as e:
            logger.error(f'Failed to save session: {e}')


    async def load_session(self, session_id: str) -> Optional[SessionData]:
        """
        Loads a session from the database. If it does not exist, return None.
        """
        if not self.is_db_configured() or not session_id:
            return None
        collection = self.client[DB_NAME][SESSIONS_COLLECTION]
        try:
            bson = await collection.find_one({'_id': session_id})
            if bson is None:
                return None
            logger.debug(f'Loaded data for session {session_id} from DB.')
            return SessionData.model_validate(bson)
        except ValidationError as e:
            logger.error(f'Invalid data for session {session_id}: {e}')
            await self.delete_session(session_id)
            delete_all_files_from_disk(session_id)
            return None
        except Exception as e:
            logger.error(f'Failed to load session {session_id}: {e}')
            return None


    async def delete_session(self, session_id: str) -> None:
        """
        Deletes a session from the database.
        """
        if not self.is_db_configured() or not session_id:
            return
        logger.debug(f'Deleting data for session {session_id} from DB.')
        collection = self.client[DB_NAME][SESSIONS_COLLECTION]
        try:
            await collection.delete_one({"_id": session_id})
        except Exception as e:
            logger.error(f'Failed to delete session {session_id}: {e}')


    async def find_session_ids(self) -> List[str]:
        if not self.is_db_configured(): return []
        collection = self.client[DB_NAME][SESSIONS_COLLECTION]
        cursor = collection.find({}, {'_id': 1})
        return [doc['_id'] async for doc in cursor]


db_client = SessionDbClient(os.environ.get('MONGODB_URI', None))


async def load_all_sessions() -> None:
    """
    Load all session data from DB into memory.
    """
    session_ids = await db_client.find_session_ids()
    logger.info(f'Loaded {len(session_ids)} sessions from DB.')
    for session_id in session_ids:
        session = await db_client.load_session(session_id)
        if session and session.is_valid():
            sessions[session_id] = session
        else:
            await delete_session(session_id)


async def create_or_refresh_session(session_id: Optional[str], max_age: int = 0) -> SessionData:
    async with (sessions_lock):
        session = sessions.get(session_id, None) \
            or await db_client.load_session(session_id)

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

    return session


def create_new_session(session_id: Optional[str] = None) -> SessionData:
    session = SessionData()
    if session_id:
        session.session_id = session_id
    return session


async def store_sessions_in_db() -> None:
    if len(sessions) == 0: return
    logger.info(f'Storing data for {len(sessions)} sessions in database...')
    async with sessions_lock:
        for session in sessions.values():
            await db_client.save_session(session)


async def cleanup_old_sessions() -> None:
    """
    Delete all expired sessions.
    """
    logger.info("Cleaning out expired sessions...")
    for session_id, session in sessions.items():
        if not session.is_valid():
            await delete_session(session_id)


async def delete_session(session_id: str) -> None:
    if session_id in sessions:
        del sessions[session_id]
    delete_all_files_from_disk(session_id)
    await db_client.delete_session(session_id)


async def delete_all_sessions() -> None:
    logger.warning("Deleting all sessions...")
    async with sessions_lock:
        for session_id in sessions:
            await db_client.delete_session(session_id)
        sessions.clear()


# LIFECYCLE

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


async def restore_scheduled_tasks(methods: dict[str, type['AbstractMethod']]) -> None:
    """"""
    for session in sessions.values():
        for task in session.scheduled_tasks.values():
            InternalTools(session, methods[task.method]).resume_scheduled_task(task)


async def on_shutdown():
    if db_client.is_db_configured():
        await store_sessions_in_db()
        await db_client.client.close()
    else:
        # without DB, sessions are lost on shutdown --> delete all files
        for session_id in sessions:
            delete_all_files_from_disk(session_id)
