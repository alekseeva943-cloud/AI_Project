# handlers/utilities/contacts.py

"""
Работа с контактами пользователей.

Содержит обработку отправленного номера
телефона и служебные функции.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import get_main_keyboard, is_admin
from config.config import CONTEXT_MESSAGE_COUNT
from database import (
    DB_PATH,
    get_all_admins,
    get_last_messages,
    save_client_info,
)


logger = logging.getLogger(__name__)


# ==========================================================
# Служебные функции.
# ==========================================================

async def show_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает Telegram ID пользователя.

    Returns:
        None.
    """

    del context

    await update.message.reply_text(
        f"Ваш ID: {update.effective_user.id}"
    )


# ==========================================================
# Обработка контактов.
# ==========================================================

async def handle_contact(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Обрабатывает контакт пользователя,
    сохраняет его в базе данных
    и пересылает администраторам.

    Returns:
        None.
    """

    try:

        contact = update.message.contact
        user = update.effective_user

        await update.message.reply_text(
            "✅ Контакт принят!\n\n"
            "Мастер скоро свяжется с вами.",
            reply_markup=get_main_keyboard(
                is_admin_user=is_admin(user.id)
            ),
        )

        # Сохраняем контакт пользователя.
        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=contact.phone_number,
        )

        # Получаем последние сообщения диалога.
        last_messages = get_last_messages(
            user.id,
            db_path=DB_PATH,
            limit=CONTEXT_MESSAGE_COUNT,
        )

        chat_link = f"tg://user?id={user.id}"

        context_text = "\n".join(
            f"{message['role']}: {message['content']}"
            for message in last_messages
        )

        manager_message = (
            "📞 Новый контакт\n\n"
            f"👤 Имя: {contact.first_name}\n"
            f"📱 Телефон: {contact.phone_number}\n"
            f"🆔 ID: {user.id}\n"
            f"💬 Чат: {chat_link}\n\n"
            f"📄 Последние сообщения ({len(last_messages)}):\n"
            f"{context_text or 'История отсутствует.'}"
        )

        # Отправляем контакт всем администраторам.
        for admin in get_all_admins(DB_PATH):

            try:

                await context.bot.send_contact(
                    chat_id=admin["user_id"],
                    phone_number=contact.phone_number,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                )

                await context.bot.send_message(
                    chat_id=admin["user_id"],
                    text=manager_message,
                )

            except Exception:
                logger.warning(
                    "Не удалось отправить контакт "
                    f"администратору {admin['user_id']}."
                )

    except Exception:
        logger.exception(
            "Ошибка обработки контакта."
        )

        await update.message.reply_text(
            "⚠️ Не удалось обработать контакт."
        )