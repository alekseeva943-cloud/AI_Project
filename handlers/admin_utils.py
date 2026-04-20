# handlers/admin_utils.py

import logging
from telegram import Update
from telegram.ext import ContextTypes

from database import get_last_messages, get_all_admins, DB_PATH
from config.config import CONTEXT_MESSAGE_COUNT

logger = logging.getLogger(__name__)


async def send_context_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user, user_message: str, gpt_answer: str):
    """Отправляет админу контекст, когда GPT дал неуверенный ответ"""
    try:
        from database import get_last_messages, get_all_admins, DB_PATH
        from config.config import CONTEXT_MESSAGE_COUNT
        import logging
        logger = logging.getLogger(__name__)

        last_messages = get_last_messages(
            user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT
        )
        context_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in last_messages]
        )

        username = f"@{user.username}" if user.username else "без логина"
        chat_link = f"tg://user?id={user.id}"

        manager_msg = (
            f"⚠️ Неуверенный запрос ({username}, ID: {user.id}):\n\n"
            f"Вопрос клиента: {user_message}\n"
            f"GPT: {gpt_answer}\n\n"
            f"📄 Последний контекст ({len(last_messages)}):\n"
            f"{context_text or 'нет истории'}\n\n"
            f"🔗 Чат: {chat_link}"
        )

        admins = get_all_admins(DB_PATH)
        for admin in admins:
            admin_id = admin['user_id']
            try:
                # Отправка контакта или локации, если есть
                if update.message and update.message.contact:
                    await context.bot.send_contact(
                        chat_id=admin_id,
                        phone_number=update.message.contact.phone_number,
                        first_name=update.message.contact.first_name,
                        last_name=update.message.contact.last_name
                    )
                elif update.message and update.message.location:
                    await context.bot.send_location(
                        chat_id=admin_id,
                        latitude=update.message.location.latitude,
                        longitude=update.message.location.longitude
                    )

                await context.bot.send_message(chat_id=admin_id, text=manager_msg)

            except Exception as send_error:
                logger.warning(
                    f"Не удалось отправить данные админу {admin_id}: {send_error}")

        logger.info(f"Неуверенный ответ от {user.id} отправлен админам")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при уведомлении админа: {e}", exc_info=True)
