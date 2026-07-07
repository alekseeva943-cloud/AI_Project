# prompts/__init__.py

"""
Загрузка промптов проекта.

Все промпты загружаются один раз
при запуске приложения.
"""

from pathlib import Path


# ==========================================================
# Константы модуля.
# ==========================================================

# Каталог с файлами промптов.
PROMPTS_DIR = Path(__file__).parent


# ==========================================================
# Загрузка промптов.
# ==========================================================

def load_prompt(filename: str) -> str:
    """
    Загружает текст промпта.

    Returns:
        str.
    """

    return (PROMPTS_DIR / filename).read_text(
        encoding="utf-8"
    )


# Основной системный промпт GPT.
SYSTEM_PROMPT = load_prompt("system_prompt.txt")

# Промпт с задачей модели.
TASK_PROMPT = load_prompt("task_prompt.txt")

# Промпт AI-роутера.
from .router_prompt import ROUTER_PROMPT