# handlers/utilities/handlers.py

"""
Регистрация служебных обработчиков.

Содержит функции регистрации
обработчиков Telegram-бота.
"""

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
)

from config import buttons as btn

from .contacts import (
    handle_contact,
    show_id,
)
from .services import (
    handle_services,
)


# ==========================================================
# Регистрация обработчиков.
# ==========================================================

def get_utility_handlers() -> list:
    """
    Возвращает список служебных
    обработчиков Telegram-бота.

    Returns:
        list.
    """

    return [
        CommandHandler(
            "id",
            show_id,
        ),
        MessageHandler(
            filters.CONTACT,
            handle_contact,
        ),
        MessageHandler(
            filters.Text(btn.BTN_SERVICES),
            handle_services,
        ),
    ]