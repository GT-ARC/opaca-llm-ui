import logging
import json
from pathlib import Path
from typing import Dict, List, Any

from .models import PromptCategory

log = logging.getLogger(__name__)

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# default-default file
DEFAULT_PROMPTS_BASE = BASE_DIR / 'default_prompts.json'

# live changes via the `POST /prompts/default` route are saved here
DEFAULT_PROMPTS_FILE = BASE_DIR / 'data' / 'default_prompts.json'


def load_default_prompts() -> Dict[str, List[PromptCategory]]:
    if DEFAULT_PROMPTS_FILE.is_file():
        data = load_json(DEFAULT_PROMPTS_FILE)
    elif DEFAULT_PROMPTS_BASE.is_file():
        data = load_json(DEFAULT_PROMPTS_BASE)
    else:
        raise FileNotFoundError('Default prompts file not found')
    return {
        key: [PromptCategory.model_validate(cat) for cat in cats]
        for key, cats in data.items()
    }


def save_default_prompts(prompts: Dict[str, List[PromptCategory]]) -> None:
    data = {
        key: [cat.model_dump() for cat in cats]
        for key, cats in prompts.items()
    }
    save_json(DEFAULT_PROMPTS_FILE, data)


def reset_default_prompts() -> None:
    from_repo = load_json(DEFAULT_PROMPTS_BASE)
    save_json(DEFAULT_PROMPTS_FILE, from_repo)


def load_json(filename: str | Path) -> Any:
    try:
        with open(filename, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log.error(f'Failed to load JSON file "{filename}"')
        raise e


def save_json(filename: str | Path, data: Any, indent: int = 4) -> None:
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=indent)
    except Exception as e:
        log.error(f'Failed to save JSON to "{filename}"')
        raise e
