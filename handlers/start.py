# handlers/start.py

"""
Обработчик команды /start.

Назначение:
- регистрация пользователя;
- сохранение информации о клиенте;
- отображение главного меню;
- возврат в главное меню без приветствия.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config.admin_keyboards import get_admin_keyboard
from config.config import is_admin
from config.keyboards import (
    get_main_keyboard,
)
from database import (
    get_client_info,
    save_client_info,
)


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Команда /start.
# ==========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Регистрирует пользователя
    и отображает главное меню.

    Returns:
        None.
    """

    del context

    user = update.effective_user

    logger.info(
        f"Пользователь {user.id} выполнил команду /start."
    )

    # Получаем сохранённые данные клиента,
    # чтобы не потерять номер телефона.
    client_data = get_client_info(user.id)

    existing_phone = (
        client_data.get("phone")
        if client_data
        else None
    )

    # Обновляем информацию о пользователе.
    save_client_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=existing_phone,
    )

    # Формируем клавиатуру
    # в зависимости от роли пользователя.
    reply_markup = (
        get_main_keyboard(is_admin_user=True)
        if is_admin(user.id)
        else get_main_keyboard()
    )

    await update.message.reply_text(
        "Добрый день!\n\n"
        "Опишите ситуацию или оставьте номер —\n"
        "мы на связи и готовы выехать немедленно.",
        reply_markup=reply_markup,
    )


# ==========================================================
# Главное меню.
# ==========================================================

async def main_menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Возвращает пользователя
    в главное меню.

    Returns:
        None.
    """

    del context

    user = update.effective_user

    logger.info(
        f"Пользователь {user.id} вернулся в главное меню."
    )

    reply_markup = (
        get_admin_keyboard()
        if is_admin(user.id)
        else get_main_keyboard()
    )

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=reply_markup,
    )