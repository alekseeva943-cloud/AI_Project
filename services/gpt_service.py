# services/gpt_service.py

"""
Работа с GPT.

Назначение:
- загрузка системных промптов;
- подготовка сообщений для GPT;
- генерация ответа модели;
- обработка ошибок OpenAI API.
"""

import logging

from openai import OpenAI
from config.config import OPENAI_API_KEY
from prompts import (
    SYSTEM_PROMPT,
    TASK_PROMPT,
)


# ==========================================================
# Клиент OpenAI.
# ==========================================================

client = OpenAI(api_key=OPENAI_API_KEY)


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Константы модуля.
# ==========================================================

# Модель, используемая для генерации ответов.
MODEL = "gpt-4o-mini"

# ==========================================================
# Генерация ответа GPT.
# ==========================================================

def generate_answer(
    query: str,
    history: list[dict] | None = None,
    context: str | None = None,
) -> str:
    """
    Генерирует ответ GPT.

    Использует системный промпт,
    дополнительный промпт с задачей,
    историю переписки и контекст RAG.

    Returns:
        str.
    """

    logger.info("🤖 GPT-запрос отправлен.")

    # Добавляем контекст базы знаний,
    # если он был найден.
    if context:
        final_task_prompt = (
            f"{TASK_PROMPT}\n\n"
            f"Контекст:\n{context}"
        )
    else:
        final_task_prompt = TASK_PROMPT

    # Формируем сообщения,
    # отправляемые модели.
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "system",
            "content": final_task_prompt,
        },
    ]

    # Добавляем последние сообщения,
    # чтобы сохранить контекст диалога.
    if history:
        messages.extend(history[-8:])

    # Добавляем текущий запрос пользователя.
    messages.append(
        {
            "role": "user",
            "content": query,
        }
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            timeout=60,
        )

        answer = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        logger.info("✅ GPT успешно ответил.")

        return answer

    except Exception:
        logger.exception(
            "Ошибка при обращении к GPT."
        )
        raise