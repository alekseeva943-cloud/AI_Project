# start.py

import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from config.config import get_admin_keyboard, get_main_keyboard, is_admin, CONTEXT_MESSAGE_COUNT
from database import DB_PATH, get_last_messages, save_client_info, get_client_info, get_all_admins, DB_PATH
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


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка и пересылка контакта + контекст"""
    try:
        contact = update.message.contact
        user = update.effective_user

        # 1. Подтверждение пользователю
        await update.message.reply_text(
            "✅ Контакт принят!\n\n"
            "Мастер сейчас свяжется с Вами.",
            reply_markup=get_main_keyboard()
        )

        # 2. Сохраняем клиента с номером телефона
        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=contact.phone_number  # Теперь передаём телефон
        )

        # 3. Получаем последние N сообщений
        last_messages = get_last_messages(
            user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT)

        # 4. Формируем текст для менеджера
        chat_link = f"tg://user?id={user.id}"
        context_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in last_messages])

        manager_msg = (
            f"📞 Новый контакт:\n"
            f"• Имя: {contact.first_name}\n"
            f"• Телефон: {contact.phone_number}\n"
            f"• Чат: {chat_link}\n"
            f"• ID пользователя: {user.id}\n\n"
            f"📄 Последний контекст ({len(last_messages)} сообщений):\n"
            f"{context_text if context_text else 'Нет истории'}"
        )

        # 5. Пересылаем всем админам
        admins = get_all_admins(DB_PATH)
        for admin in admins:
            admin_id = admin['user_id']
            try:
                await context.bot.send_contact(
                    chat_id=admin_id,
                    phone_number=contact.phone_number,
                    first_name=contact.first_name,
                    last_name=contact.last_name
                )
                await context.bot.send_message(chat_id=admin_id, text=manager_msg)
            except Exception as ex:
                logger.warning(
                    f"Не удалось отправить контакт админу {admin_id}: {ex}")
    except Exception as e:
        logger.error(f"Ошибка обработки контакта: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка обработки контакта")
