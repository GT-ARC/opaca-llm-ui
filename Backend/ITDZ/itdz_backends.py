from typing import Dict

import requests
import random

from ..models import Response, AgentMessage


class ProxyBackend:

    def __init__(self):
        self.config = self._init_config()

    async def history(self) -> list:
        return []

    async def reset(self):
        pass

    async def get_config(self) -> dict:
        return self.config

    async def set_config(self, conf: dict):
        self.config = {k: conf.get(k, v) for k, v in self.config.items()}


class KnowledgeBackend(ProxyBackend):

    def _init_config(self):
        return {
            "url": "http://10.0.4.59:8000/chat-{model}",
            "model": "ollama",
            "conv_id": random.randint(1000, 10000),
            "msg_id": 0,
        }

    async def reset(self):
        self.config["conv_id"] = random.randint(1000, 10000)

    async def query(self, message: str, debug: bool, api_key: str) -> Response:
        print("QUERY", message)
        url = self.config["url"].format(model=self.config["model"])
        json = {
            "conv_id": self.config["conv_id"],
            "msg_id": self.config["msg_id"] + 1,
            "role": "user",
            "content": message,
            "rating": 0
        }
        response = requests.post(url, json=json)
        response.raise_for_status()
        result = response.json()
        print("RESULT", result)
        self.config["msg_id"] = int(result["msg_id"])
        return Response(query=message, content=result["content"])


class DataAnalysisBackend(ProxyBackend):

    def _init_config(self):
        return {
            "url": "http://10.42.6.107:3002/ask_csv",
        }

    async def query(self, message: str, debug: bool, api_key: str) -> Response:
        print("QUERY", message)
        url = self.config["url"]
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
