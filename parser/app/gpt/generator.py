# Модуль генерации текста с помощью GPT
"""
generator.py

Модуль отвечает за генерацию ответа через GPT.

Что делает:
1. Загружает промпт из файла
2. Подставляет контекст и вопрос
3. Отправляет запрос в OpenAI
4. Возвращает структурированный ответ

Важно:
Отделён от поиска и базы — только генерация.
"""

from openai import OpenAI

from app.config.settings import (
    GPT_MODEL,
    GPT_MAX_TOKENS,
    GPT_TEMPERATURE,
    PROMPT_ANSWER_PATH,
)

from app.utils.logger import logger


# =========================
# 📄 Загрузка промпта
# =========================
def load_prompt(path: str) -> str:
    """
    Загружает текст промпта из файла.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# =========================
# 🧠 КЛАСС GENERATOR
# =========================
class GPTGenerator:
    """
    Класс для генерации ответов через GPT.
    """

    def __init__(self):
        self.client = OpenAI()

        # загружаем промпт один раз
        self.prompt_template = load_prompt(PROMPT_ANSWER_PATH)

        logger.info(f"🤖 GPTGenerator инициализирован: {GPT_MODEL}")

    # =========================
    # 🚀 Генерация ответа
    # =========================

    def generate(self, query: str, context: str) -> str:
        """
        Генерирует ответ на основе контекста и вопроса.
        """

        logger.info("🤖 Генерация ответа")

        # подставляем данные в шаблон
        prompt = self.prompt_template.format(
            context=context,
            question=query
        )

        response = self.client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=GPT_MAX_TOKENS,
            temperature=GPT_TEMPERATURE
        )

        answer = response.choices[0].message.content

        logger.info("✅ Ответ сгенерирован")

        return answer
