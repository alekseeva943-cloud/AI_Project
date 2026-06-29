# Модуль токенизации с использованием tiktoken
"""
tokenizer.py

Модуль отвечает за работу с токенами (через tiktoken).

Что делает:
1. Инициализирует tokenizer под нужную модель
2. Считает количество токенов
3. Преобразует текст в токены

Важно:
Используется перед chunking, чтобы контролировать размер чанков.
"""

import tiktoken
from app.config.settings import TOKENIZER_MODEL
from app.utils.logger import logger


# =========================
# 🧠 КЛАСС TOKENIZER
# =========================
class Tokenizer:
    """
    Класс-обёртка над tiktoken.

    Позволяет:
    - считать токены
    - централизованно управлять моделью
    """

    def __init__(self, model: str = TOKENIZER_MODEL):
        """
        Инициализация tokenizer.

        Python делает:
        1. берёт модель из settings
        2. создаёт encoding
        """

        self.model = model

        self.encoding = tiktoken.encoding_for_model(model)

        logger.info(f"🧠 Tokenizer инициализирован: {model}")

    # =========================
    # 🔢 Подсчёт токенов
    # =========================

    def count(self, text: str) -> int:
        """
        Считает количество токенов в тексте.
        """

        return len(self.encoding.encode(text))

    # =========================
    # 🔄 Текст → токены
    # =========================

    def encode(self, text: str) -> list:
        """
        Преобразует текст в список токенов.
        """

        return self.encoding.encode(text)

    # =========================
    # 🔄 Токены → текст
    # =========================

    def decode(self, tokens: list) -> str:
        """
        Преобразует токены обратно в текст.
        """

        return self.encoding.decode(tokens)
