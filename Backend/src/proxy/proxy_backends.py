import httpx
import random

from ..models import Response, SessionData, OpacaLLMBackend, ConfigParameter


class KnowledgeBackend(OpacaLLMBackend):
    NAME = "itdz-knowledge"

    @property
    def config_schema(self):
        return {
            "url": ConfigParameter(type="string", required=True, default="http://10.0.4.59:8000/chat-{model}"),
            "model": ConfigParameter(type="string", required=True, default="ollama"),
            "conv_id": ConfigParameter(type="integer", required=True, default=random.randint(1000, 10000)),
            "msg_id": ConfigParameter(type="integer", required=True, default=0),
        }

    async def query(self, message: str, session: SessionData) -> Response:
        print("QUERY", message)
        config = session.config.get(KnowledgeBackend.NAME, self.default_config())
        url = config["url"].format(model=config["model"])
        json = {
            "conv_id": config["conv_id"],
            "msg_id": config["msg_id"] + 1,
            "role": "user",
            "content": message,
            "rating": 0
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=json)
        response.raise_for_status()
        result = response.json()
        print("RESULT", result)
        config["msg_id"] = int(result["msg_id"])
        return Response(query=message, content=result["content"])


class DataAnalysisBackend(OpacaLLMBackend):
    NAME = "itdz-data"

    @property
    def config_schema(self):
        return {
            "url": ConfigParameter(type="string", required=True, default="http://10.42.6.107:3002/ask_csv"),
        }

    async def query(self, message: str, session: SessionData) -> Response:
        print("QUERY", message)
        config = session.config.get(DataAnalysisBackend.NAME, self.default_config())
        url = config["url"]
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"question": message})
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
