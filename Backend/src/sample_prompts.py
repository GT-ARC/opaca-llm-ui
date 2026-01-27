import logging
import json
from pathlib import Path
from typing import Dict, List, Any

from .models import PromptCategory

logger = logging.getLogger(__name__)

DEFAULT_PROMPTS_FILE = Path('./data/default_prompts.json')


def load_default_prompts() -> Dict[str, List[PromptCategory]]:
    if not DEFAULT_PROMPTS_FILE.is_file():
        raise FileNotFoundError('Default prompts file not found')
    return {
        key: [PromptCategory.model_validate(cat) for cat in cats]
        for key, cats in load_json(DEFAULT_PROMPTS_FILE).items()
    }


def save_default_prompts(prompts: Dict[str, List[PromptCategory]]) -> None:
    data = {
        key: [cat.model_dump() for cat in cats]
        for key, cats in prompts.items()
    }
    save_json(DEFAULT_PROMPTS_FILE, data)


def get_default_prompts(key: str) -> List[PromptCategory]:
    data = load_default_prompts()
    if key not in data:
        raise KeyError(f'Invalid default prompts key: {key}')
    return data[key]


def load_json(filename: str | Path) -> Any:
    with open(filename, encoding='utf-8') as f:
        return json.load(f)


def save_json(filename: str | Path, data: Any, indent: int = 4) -> None:
    with open(filename, 'w') as f:
        json.dump(data, f, indent=indent)
