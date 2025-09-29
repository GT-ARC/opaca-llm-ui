from typing import Optional
from pymongo.asynchronous.mongo_client import AsyncMongoClient
import logging

from .models import SessionData

DB_NAME: str = 'backend-data'
SESSIONS_COLLECTION: str = 'sessions'

logger = logging.getLogger(__name__)


def __get_client(uri: Optional[str] = None) -> AsyncMongoClient:
    if uri is None:
        uri = 'mongodb://user:pass@backend-db:27017'
    return AsyncMongoClient(uri)


async def save_session(session: SessionData) -> None:
    """
    Saves a session to the database. Replace the existing one if session_id matches.
    """
    if session is None:
        return
    bson = session.model_dump(mode='json', by_alias=True)
    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        await collection.replace_one({"_id": session.session_id}, bson, upsert=True)


async def load_session(session_id: str) -> Optional[SessionData]:
    """
    Loads a session from the database. If it does not exist, return None.
    """
    if not session_id:
        return None

    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        try:
            bson = await collection.find_one({"_id": session_id})
            if bson is None:
                return None
            return SessionData.model_validate(bson)
        except Exception as e:
            logger.error(f'Failed to load session {session_id}: {e}')
            return None


async def delete_session(session_id: str) -> None:
    """
    Deletes a session from the database.
    """
    if not session_id:
        return

    async with __get_client() as client:
        collection = client[DB_NAME][SESSIONS_COLLECTION]
        try:
            await collection.delete_one({"_id": session_id})
        except Exception as e:
            logger.error(f'Failed to delete session {session_id}: {e}')
