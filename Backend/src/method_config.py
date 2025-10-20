from pydantic import BaseModel, Field, create_model
from typing import Annotated, Dict, List, Any

from .models import get_supported_models


class MethodConfig:
    """
    This config class is a builder-type class that dynamically
    builds the config required by the backend method.
    """

    def __init__(self, method_name: str) -> None:
        self.method_name = method_name
        self.parameters: Dict[str, Any] = {}
        self._class: type[BaseModel] | None = None

    def string(self, name: str, default: str = '', options: List[str] = None, title: str = None, description: str = None) -> 'MethodConfig':
        self.parameters[name] = Annotated[str, Field(
            default=default,
            title=title, description=description,
            json_schema_extra={'options': options},
        )]
        return self

    def integer(self, name: str, default: int = 1, min: int = 1, max: int = 10, step: int = 1, title: str = None, description: str = None) -> 'MethodConfig':
        self.parameters[name] = Annotated[int, Field(
            default=default,
            title=title, description=description,
            ge=min, le=max, multiple_of=step,
        )]
        return self

    def number(self, name: str, default: float = 0, min: float = 0, max: float = 2, step: float = 0.1, title: str = None, description: str = None) -> 'MethodConfig':
        self.parameters[name] = Annotated[float, Field(
            default=default,
            title=title, description=description,
            ge=min, le=max, multiple_of=step,
        )]
        return self

    def boolean(self, name: str, default: bool = False, title: str = None, description: str = None) -> 'MethodConfig':
        self.parameters[name] = Annotated[bool, Field(
            default=default,
            title=title, description=description,
        )]
        return self

    def get_class(self, force_recreate: bool = False) -> type[BaseModel]:
        if self._class is None or force_recreate:
            self._class = create_model(f'{self.method_name}_Config', **self.parameters)
        return self._class

    def get_schema(self) -> Dict[str, Any]:
        return self.get_class().model_json_schema(mode='serialization')

    def validate(self, config: Dict[str, Any]) -> BaseModel:
        return self.get_class().model_validate(config)

    def instantiate(self) -> BaseModel:
        return self.get_class()()

    ### default params ###

    def llm(self, name: str, title: str = None, description: str = None) -> 'MethodConfig':
        models = [f"{url}::{model}"
                  for url, _, models in get_supported_models()
                  for model in models]
        return self.string(name, default=models[0], options=models, title=title, description=description)

    def temperature(self, default: float = 0, min: float = 0, max: float = 2, step: float = 0.1) -> 'MethodConfig':
        return self.number('temperature', default=default, min=min, max=max, step=step, title='Temperature', description='Temperature for the models')

    def max_rounds(self, default: int = 1, min: int = 1, max: int = 10, step: int = 1) -> 'MethodConfig':
        return self.integer('max_repetitions', default=default, min=min, max=max, step=step, title='Max Rounds', description='Maximum number of retries')
