"""
handlers/admin/client_messages.py

Отправка сообщений клиентам из административной панели.

Модуль отвечает за:

- начало диалога с клиентом;
- отправку сообщений клиенту;
- отмену режима написания сообщения.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config.admin_keyboards import get_admin_keyboard
from config.keyboards import get_cancel_keyboard
from config import buttons as btn

from database import (
    add_message,
    get_client_info,
    mark_user_blocked,
)

from handlers.admin.panel import show_admin_panel
from handlers.admin.constants import (
    AWAITING_MESSAGE_TO_CLIENT,
)

logger = logging.getLogger(__name__)

# Запускает режим отправки сообщения конкретному клиенту.
async def start_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cancel_target"] = show_admin_panel
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Неверный ID клиента.")
        return ConversationHandler.END

    context.user_data['writing_to'] = user_id
    client_info = get_client_info(user_id)
    if not client_info:
        await query.message.reply_text("❌ Клиент не найден.")
        return ConversationHandler.END

    name = (client_info['first_name'] or '') + \
        (' ' + (client_info['last_name'] or ''))
    name = name.strip() or "Клиент"
    username = client_info.get('username')
    target = f'<a href="tg://resolve?domain={username}">@{username}</a>' if username else f"ID: <code>{user_id}</code>"

    await query.message.reply_text(
        f"✏️ Введите сообщение для {target}:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_MESSAGE_TO_CLIENT


# Отправляет введённое администратором сообщение клиенту.
async def send_message_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == btn.BTN_CANCEL:
        context.user_data.pop('writing_to', None)
        await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    user_id = context.user_data.get('writing_to')
    if not user_id:
        await update.message.reply_text("❌ Ошибка: не указан получатель.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Пустое сообщение.")
        return AWAITING_MESSAGE_TO_CLIENT

    try:
        await context.bot.send_message(chat_id=user_id, text=text)
        add_message(user_id=user_id, role='assistant', content=text)
    except Exception as e:
        logger.error(f"Не удалось отправить {user_id}: {e}")
        if any(err in str(e) for err in ["bot was blocked", "user is deactivated", "chat not found"]):
            mark_user_blocked(user_id)
        await update.message.reply_text("❌ Не удалось отправить. Возможно, клиент заблокировал бота.", reply_markup=get_admin_keyboard())
        context.user_data.pop('writing_to', None)
        return ConversationHandler.END

    client_info = get_client_info(user_id)
    name = (client_info['first_name'] or '') + (' ' +
                                                (client_info['last_name'] or '')) if client_info else ""
    name = name.strip() or "Клиент"
    username = client_info.get('username') if client_info else None
    target = f'<a href="tg://resolve?domain={username}">@{username}</a>' if username else f"ID: <code>{user_id}</code>"

    context.user_data.pop('writing_to', None)
    await update.message.reply_text(f"✅ Сообщение отправлено {target}!", parse_mode="HTML", reply_markup=get_admin_keyboard())
    return ConversationHandler.END

# Отменяет режим написания сообщения клиенту.
async def cancel_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('writing_to', None)
    await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
    return ConversationHandler.END