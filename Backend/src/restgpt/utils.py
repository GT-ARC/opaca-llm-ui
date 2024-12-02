import requests

from typing import Optional, List, Dict, Any, Union, Sequence, Tuple
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate, MessagesPlaceholder, \
    HumanMessagePromptTemplate, AIMessagePromptTemplate
from langchain_core.runnables import RunnableConfig


LLAMA_URL = "http://10.0.64.101"


class OpacaLLM(BaseChatModel):

    url: str = ""
    model: str = ""

    def __init__(self, url, model, **data: Any):
        super().__init__(**data)
        self.url = url
        self.model = model

    @property
    def _llm_type(self) -> str:
        return "Llama-3 Proxy"

    def invoke(
            self,
            input: Union[PromptValue, str, Sequence[Union[BaseMessage, List[str], Tuple[str, str], str, Dict[str, Any]]]],
            config: Optional[RunnableConfig] = None,
            *,
            stop: Optional[List[str]] = None,
            **kwargs: Any
    ) -> str:
        return self._generate(format_llama3(input), stop)

    def _generate(
            self,
            prompt: Any,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any
    ) -> str:
        response = requests.post(
            f'{self.url}/api/chat',
            json={
                'messages': prompt,
                'model': self.model,
                'stream': False,
            }
        ).json()['message']['content']

        output = response.replace("\\n", "\n").replace('\\"', '"').strip()

        if stop is None:
            return output

        for word in stop:
            stop_pos = output.find(word)
            if stop_pos != -1:
                return output[:stop_pos].strip()

        return output


def build_prompt(
        system_prompt: str,
        examples: List[Dict[str, str]],
        input_variables: List[str],
        message_template: str
    ) -> ChatPromptTemplate:

    example_prompt = ChatPromptTemplate.from_messages(
        [
            HumanMessagePromptTemplate.from_template("{input}"),
            AIMessagePromptTemplate.from_template("{output}")
        ]
    )

    few_shot_prompt = FewShotChatMessagePromptTemplate(
        input_variables=input_variables,
        example_prompt=example_prompt,
        examples=examples
    )

    final_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            few_shot_prompt,
            MessagesPlaceholder(variable_name="history", optional=True),
            ("human", message_template),
        ]
    )

    return final_prompt


def format_llama3(prompt_values: PromptValue):
    messages = []

    for message in prompt_values.to_messages():
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            raise ValueError(f'Unknown message type: {type(message)}')

        content = message.content
        content = content.replace("\\n", "").replace('\\"', '"')

        messages.append({"role": role, "content": content})
    return messages
