import requests


class BackendTestClient:
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    # BACKEND API ROUTES

    def alive(self):
        res = requests.get(f"{self.base_url}/docs", timeout=10)
        return res.status_code == 200

    def get_backends(self) -> list:
        return self.request("GET", "/backends")

    def get_models(self) -> dict[str, list[str]]:
        return self.request("GET", "/models")

    def connect(self, url) -> int:
        body = {"url": url, "user": None, "pwd": None}
        return self.request("POST", "/connect", body)

    def get_actions(self) -> dict[str, list[dict]]:
        return self.request("GET", "/actions")

    def query_no_history(self, backend: str, query: str) -> dict:
        body = {"user_query": query}
        return self.request("POST", f"/query/{backend}", body)

    def reset_all(self):
        return self.request("POST", "/reset_all")

    def get_chats(self) -> list[dict]:
        return self.request("GET", f"/chats")

    def get_chat_history(self, chat_id: str) -> dict:
        return self.request("GET", f"/chats/{chat_id}")

    def query_chat(self, backend: str, chat_id: str, query: str) -> dict:
        body = {"user_query": query}
        return self.request("POST", f"/chats/{chat_id}/query/{backend}", body)

    def update_chat(self, chat_id: str, new_name: str) -> None:
        body = {"new_name": new_name}
        return self.request("PUT", f"/chats/{chat_id}", body)

    def delete_chat(self, chat_id: str) -> bool:
        return self.request("DELETE", f"/chats/{chat_id}")

    def search_chats(self, query: str) -> dict[str, list[dict]]:
        body = {"query": query}
        return self.request("POST", "/chats/search", body)

    def get_config(self, backend: str) -> dict:
        return self.request("GET", f"/config/{backend}")

    def set_config(self, backend: str, conf: dict) -> dict:
        return self.request("PUT", f"/config/{backend}", conf)

    def reset_config(self, backend: str) -> dict:
        return self.request("DELETE", f"/config/{backend}")

    # HELPER METHODS

    def request(self, method, route, body=None):
        res = self.session.request(method, f"{self.base_url}{route}", json=body, timeout=60)
        try:
            res.raise_for_status()
        except Exception as e:
            print("ERROR", repr(e))
            assert False
        return res.json()
