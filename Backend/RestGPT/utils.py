import os
import re
import json
import requests
from typing import Optional, List, Dict, Any
from logging.handlers import BaseRotatingHandler
from colorama import Fore

from langchain.agents.agent_toolkits.openapi.spec import ReducedOpenAPISpec
from langchain_core.language_models.llms import LLM


class ColorPrint:
    def __init__(self):
        self.color_mapping = {
            "Planner": Fore.RED,
            "API Selector": Fore.YELLOW,
            "Caller": Fore.BLUE,
            "Final Answer": Fore.GREEN,
            "Code": Fore.WHITE,
        }

    def write(self, data):
        module = data.split(':')[0]
        if module not in self.color_mapping:
            print(data, end="")
        else:
            print(self.color_mapping[module] + data + Fore.RESET, end="")


class OpacaLLM:
    server_url: str
    stop_words: Optional[List[str]]

    def __init__(self, server_url: str, stop_words: Optional[List[str]] = None):
        self.server_url = server_url
        self.stop_words = stop_words

    def bind(self, **kwargs):
        stop_words = kwargs.get('stop', self.stop_words)
        return OpacaLLM(server_url=self.server_url, stop_words=stop_words)

    def call(self, inputs: List[Dict[str, Any]]) -> str:
        response = requests.post(f'{self.server_url}/llama-3/chat', json={'messages': inputs})

        output = response.text.replace("\\n", "\n").replace('\\"', '"')
        output = output.strip('"')

        if self.stop_words is None:
            return output

        for stop_word in self.stop_words:
            stop_pos = output.find(stop_word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return output
