import logging
from pathlib import Path
from typing import Dict, List

from .file_utils import load_json, save_json
from .models import PromptCategory

logger = logging.getLogger(__name__)

DEFAULT_PROMPTS_FILE = Path('./data/default_prompts.json')


def load_default_prompts() -> Dict[str, List[PromptCategory]]:
    print(DEFAULT_PROMPTS_FILE.absolute().resolve())
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
    if key is not None and key not in data:
        raise KeyError(f'Invalid default prompts key: {key}')
    return data[key]