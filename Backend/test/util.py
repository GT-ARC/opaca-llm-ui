from typing import Union, Optional
from fastapi import Request, Response

from starlette.datastructures import Headers
from starlette.websockets import WebSocket

from src.models import SessionData, OpacaException
from src.session_manager import create_or_refresh_session


def example_prompt():
    return {
        "GB": [
            {
                "id": "testSection",
                "header": "TestSection",
                "icon": "🤖",
                "visible": False,
                "questions": [
                    {
                        "question": "This is a test question",
                        "icon": "🔧"
                    }
                ]
            }
        ]
    }

async def handle_admin_session_id(source: Request, response: Response) -> SessionData:
    return await handle_test_session_id("admin", source, response)

async def handle_user_session_id(source: Request, response: Response) -> SessionData:
    return await handle_test_session_id("user", source, response)

async def handle_test_session_id(session_id: str, source: Union[Request, WebSocket], response: Optional[Response] = None) -> SessionData:
    """
    Unified session handler for both HTTP requests and WebSocket connections.
    If no valid session ID is found, a new one is created and optionally set in the response cookie.
    """

    # Extract cookies from headers
    headers = Headers(scope=source.scope)
    cookies = headers.get("cookie")
    session_id = session_id

    # Extract session_id from cookies
    if cookies:
        cookie_dict = dict(cookie.split("=", 1) for cookie in cookies.split("; "))
        session_id = cookie_dict.get("session_id", None)

    max_age = 60 * 60 * 24 * 30  # 30 days
    # create Cookie (or just update max-age if already exists)
    session = await create_or_refresh_session(session_id, max_age)

    if session.blocked:
        raise OpacaException("The session has been blocked. If you think this is an error, please consult the platform administrator.")

    # If it's an HTTP request, and you want to set a cookie
    if response is not None:
        response.set_cookie("session_id", session.session_id, max_age=max_age)

    # Return the session data for the session ID
    return session
