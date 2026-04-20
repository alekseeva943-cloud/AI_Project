# gpt_service.py

import os
from openai import OpenAI
from config.config import OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-4o-mini"


# =======================
# 🔹 ЗАГРУЗКА ПРОМПТОВ
# =======================

# абсолютный путь к корню проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_prompt(filename: str) -> str:
    path = os.path.join(BASE_DIR, "prompts", filename)

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


SYSTEM_PROMPT = load_prompt("system_prompt.txt")
TASK_PROMPT = load_prompt("task_prompt.txt")


# =======================
# 🔹 GPT ГЕНЕРАЦИЯ
# =======================

def generate_answer(query: str, history: list = None, context: str = None):

    # 🔥 формируем task_prompt
    if context:
        final_task_prompt = f"{TASK_PROMPT}\n\nКонтекст:\n{context}"
    else:
        final_task_prompt = TASK_PROMPT

    # 🔥 сообщения
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": final_task_prompt}
    ]

    # 🔥 история
    if history:
        messages.extend(history[-8:])

    # 🔥 текущий запрос
    messages.append({"role": "user", "content": query})

    # 🔥 запрос к GPT
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
