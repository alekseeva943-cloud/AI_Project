#router_service.py

"""
AI-роутер запросов.

Определяет намерение пользователя (intent)
и возвращает результат в формате JSON.
"""

import json

from openai import OpenAI
from config.config import OPENAI_API_KEY
from prompts.router_prompt import SYSTEM_PROMPT

# ==========================================================
# Клиент OpenAI.
# ==========================================================

client = OpenAI(api_key=OPENAI_API_KEY)


# ==========================================================
# Константы модуля.
# ==========================================================

# Модель, используемая для определения intent.
MODEL = "gpt-4o-mini"


# ==========================================================
# Определение намерения пользователя.
# ==========================================================

def classify_intent(
    query: str,
    history: list[dict] | None = None,
) -> dict:
    """
    Определяет намерение пользователя.

    Returns:
        dict.
    """

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    # Добавляем несколько последних сообщений,
    # чтобы сохранить контекст диалога.
    if history:
        messages.extend(history[-5:])

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
            temperature=0,
        )

        content = response.choices[0].message.content.strip()

        return json.loads(content)

    except Exception:
        return {"intent": "unknown"}