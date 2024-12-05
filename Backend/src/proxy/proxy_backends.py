import requests
import random

from ..models import Response, SessionData


class ProxyBackend:

    async def get_config(self) -> dict:
        return self._get_config()


class KnowledgeBackend(ProxyBackend):
    NAME = "itdz-knowledge"

    @staticmethod
    def _get_config():
        return {
            "url": "http://10.0.4.59:8000/chat-{model}",
            "model": "ollama",
            "conv_id": random.randint(1000, 10000),
            "msg_id": 0,
        }

    async def query(self, message: str, debug: bool, api_key: str, session: SessionData) -> Response:
        print("QUERY", message)
        config = session.get(KnowledgeBackend.NAME, self._get_config())
        url = config["url"].format(model=config["model"])
        json = {
            "conv_id": config["conv_id"],
            "msg_id": config["msg_id"] + 1,
            "role": "user",
            "content": message,
            "rating": 0
        }
        response = requests.post(url, json=json)
        response.raise_for_status()
        result = response.json()
        print("RESULT", result)
        config["msg_id"] = int(result["msg_id"])
        return Response(query=message, content=result["content"])


class DataAnalysisBackend(ProxyBackend):
    NAME = "itdz-data"

    @staticmethod
    def _get_config():
        return {
            "url": "http://10.42.6.107:3002/ask_csv",
        }

    async def query(self, message: str, debug: bool, api_key: str, session: SessionData) -> Response:
        print("QUERY", message)
        config = session.get(DataAnalysisBackend.NAME, self._get_config())
        url = config["url"]
        response = requests.post(url, json={"question": message})
        response.raise_for_status()
        result = response.json()
        print("RESULT", result)
        if result["type"] == "answer":
            return Response(query=message, content=f"{result['content']}")
        elif result["type"] == "plot":
            img_url = f"{url[:url.rfind('/')]}/get_image/{result['content']}"
            return Response(query=message, content=f'<img src="{img_url}" width="100%">')
        else:
            return Response(query=message, content=str(result))
