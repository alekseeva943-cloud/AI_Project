"""
keyboards.py

Модуль отвечает за все кнопки Telegram-бота.

Что делает:
1. Формирует главное меню
2. Включает/выключает кнопки через settings
"""

from telegram import ReplyKeyboardMarkup

from app.config.settings import (
    ENABLE_BUILD_BUTTON,
    ENABLE_SEARCH_BUTTON,
    ABOUT_BUTTON
)


def get_main_keyboard():
    """
    Создаёт клавиатуру на основе настроек.
    """

    keyboard = []

    if ENABLE_BUILD_BUTTON:
        keyboard.append(["🚀 Построить базу"])

    if ENABLE_SEARCH_BUTTON:
        keyboard.append(["🔍 Задать вопрос"])

    if ABOUT_BUTTON:
        keyboard.append(["📌 О проекте"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
