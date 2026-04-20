# router_service.py

import json
from openai import OpenAI
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """
Ты — AI-роутер.

Задача:
определить intent пользователя.

Типы:
- small_talk
- info
- problem
- lead
- unknown

Правила:
- хочет вызвать / срочно / приехать → lead
- описывает проблему → problem
- спрашивает → info
- общается → small_talk

ВАЖНО:
верни ТОЛЬКО JSON

Формат:
{
  "intent": "..."
}
"""


def classify_intent(query: str, history: list = None) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    if history:
        messages.extend(history[-5:])

    messages.append({"role": "user", "content": query})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except Exception:
        return {"intent": "unknown"}
