import time
from typing import Optional
from pymongo.asynchronous.mongo_client import AsyncMongoClient
import asyncio
import logging

from src.models import SessionData


DB_NAME: str = 'backend-data'
SESSIONS_COLLECTION: str = 'sessions'


logger = logging.getLogger(__name__)

__client = AsyncMongoClient(host="localhost", port=27017)


async def save_session(session: SessionData) -> None:
    """
    Saves a session to the database.
    """
    if session is None:
        return

    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    bson = session.model_dump(mode='json', by_alias=True)

    try:
        await collection.replace_one({"_id": session.session_id}, bson, upsert=True)
    except Exception as e:
        logger.error(f'Failed to save session: {e}')


async def load_session(session_id: str) -> Optional[SessionData]:
    """
    Loads a session from the database. If it does not exist, return None.
    """
    collection = __client[DB_NAME][SESSIONS_COLLECTION]
    bson = await collection.find_one({"_id": session_id})
    if bson is None:
        return None

    try:
        return SessionData.model_validate(bson)
    except Exception as e:
        logger.error(f'Failed to load session: {e}')
        return None


async def delete_session(session_id: str) -> None:
    """
    Deletes a session from the database.
    """
    collection = __client[DB_NAME][SESSIONS_COLLECTION]

    try:
        await collection.delete_one({"_id": session_id})
    except Exception as e:
        logger.error(f'Failed to delete session: {e}')
