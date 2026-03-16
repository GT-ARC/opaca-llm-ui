from typing import Union, Optional
from fastapi import Request, Response
import requests

from starlette.datastructures import Headers
from starlette.websockets import WebSocket

from Backend.src.models import SessionData, OpacaException
from Backend.src.session_manager import create_or_refresh_session


class BackendTestClient:
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    # BACKEND API ROUTES

    def alive(self):
        res = requests.get(f"{self.base_url}/docs", timeout=10)
        return res.status_code == 200

    def get_methods(self) -> list:
        return self.request("GET", "/methods")

    def get_models(self) -> dict[str, list[str]]:
        return self.request("GET", "/models")

    def connect(self, url) -> int:
        body = {"url": url, "user": None, "pwd": None}
        return self.request("POST", "/connect", body)

    def get_actions(self) -> dict[str, list[dict]]:
        return self.request("GET", "/actions")

    def query_no_history(self, method: str, query: str) -> dict:
        body = {"user_query": query}
        return self.request("POST", f"/query/{method}", body)

    def get_chats(self) -> list[dict]:
        return self.request("GET", f"/chats")
    
    def delete_chats(self) -> bool:
        return self.request("DELETE", f"/chats")

    def get_chat_history(self, chat_id: str) -> dict:
        return self.request("GET", f"/chats/{chat_id}")

    def query_chat(self, method: str, chat_id: str, query: str) -> dict:
        body = {"user_query": query}
        return self.request("POST", f"/chats/{chat_id}/query/{method}", body)

    def update_chat(self, chat_id: str, new_name: str) -> None:
        body = {"new_name": new_name}
        return self.request("PUT", f"/chats/{chat_id}", body)

    def delete_chat(self, chat_id: str) -> bool:
        return self.request("DELETE", f"/chats/{chat_id}")

    def search_chats(self, query: str) -> dict[str, list[dict]]:
        body = {"query": query}
        return self.request("POST", "/chats/search", body)

    def get_config(self, method: str) -> dict:
        return self.request("GET", f"/config/{method}")

    def set_config(self, method: str, conf: dict) -> dict:
        return self.request("PUT", f"/config/{method}", conf)

    def reset_config(self, method: str) -> dict:
        return self.request("DELETE", f"/config/{method}")

    # HELPER METHODS

    def request(self, method, route, body=None):
        res = self.session.request(method, f"{self.base_url}{route}", json=body, timeout=120)
        try:
            res.raise_for_status()
        except Exception as e:
            print("ERROR", repr(e))
            assert False
        return res.json()

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
