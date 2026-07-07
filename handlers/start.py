# start.py

import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config.config import is_admin, CONTEXT_MESSAGE_COUNT
from config.keyboards import get_main_keyboard
from config.admin_keyboards import get_admin_keyboard
from database import (
    DB_PATH,
    get_all_admins,
    get_client_info,
    get_last_messages,
    save_client_info,
)
from handlers.admin import show_admin_panel
from handlers.menu import main_menu_handler
import logging


logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — начальное приветствие"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запустил /start")

    welcome_text = (
        "Добрый день!\n\n"
        "Опишите ситуацию или оставьте номер —\n"
        "мы на связи и готовы выехать немедленно."
    )

    # Получаем текущую информацию о клиенте (если есть)
    client_data = get_client_info(user.id)
    existing_phone = client_data.get('phone') if client_data else None

    # Сохраняем пользователя с сохранением телефона, если он был
    save_client_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=existing_phone  # Не удаляем телефон, если он уже был
    )

    # Формируем клавиатуру
    if is_admin(user.id):
        reply_markup = get_main_keyboard(is_admin_user=True)
    else:
        reply_markup = get_main_keyboard()

    # Отправляем сообщение
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает главное меню без приветствия"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} вернулся в главное меню")

    if is_admin(user.id):
        reply_markup = get_admin_keyboard()
    else:
        reply_markup = get_main_keyboard()

    await update.message.reply_text("Выберите услугу:", reply_markup=reply_markup)
