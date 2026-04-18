import logging
import json

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, Application

from config.config import (
    ADMIN_QUEUE,
    SYSTEM_PROMPT,
    CONTEXT_MESSAGE_COUNT,
    UNCERTAIN_MESSAGE
)

from database import (
    save_client_info,
    add_message,
    get_last_messages,
    DB_PATH,
    get_client_info
)

from handlers.start import start as main_menu_handler
from services.gpt_service import ask_gpt

logger = logging.getLogger(__name__)


# =======================
# 🔹 Бизнес-правила
# =======================

def is_uncertain_response(text: str) -> bool:
    triggers = ["не знаю", "не уверен", "уточните", "думаю", "скорее всего"]
    return any(t in text.lower() for t in triggers)


def should_notify_manager(text: str) -> bool:
    triggers = ["перезвонит", "свяжется", "мы вам позвоним", "ожидайте"]
    return any(t in text.lower() for t in triggers)


# =======================
# 🔹 Уведомление админов
# =======================

async def notify_manager(context: ContextTypes.DEFAULT_TYPE, message: str):
    from database import get_all_admins

    admins = get_all_admins(DB_PATH)

    for admin in admins:
        admin_id = admin['user_id']
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
        except Exception:
            ADMIN_QUEUE.setdefault(admin_id, []).append(message)


# =======================
# 🔹 GPT helper
# =======================

async def generate_gpt_answer(messages):
    return await ask_gpt(messages)


# =======================
# 🔹 Основной handler
# =======================

async def handle_gpt_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = update.message.text

        # --- фильтр ---
        if text.startswith('/') or text == "💬 Задать вопрос":
            return

        if text == "⬅️ Вернуться":
            await main_menu_handler(update, context)
            return

        # --- клиент ---
        client_info = get_client_info(user.id)
        phone = client_info.get('phone') if client_info else None

        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=phone
        )

        add_message(user.id, "user", text)

        # --- история ---
        history = get_last_messages(
            user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT
        )

        system_prompt = context.user_data.get("system_prompt", SYSTEM_PROMPT)

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": text}
        ]

        await update.message.reply_chat_action("typing")

        # 🔥 GPT В ОДНОЙ СТРОКЕ
        gpt_answer = await generate_gpt_answer(messages)

        if gpt_answer.strip():
            add_message(user.id, "assistant", gpt_answer)

        # =======================
        # 🔹 Проверки
        # =======================

        if is_uncertain_response(gpt_answer):
            await notify_manager(
                context,
                f"⚠️ Неуверенный ответ\n{user.id}\n{text}\n{gpt_answer}"
            )

        if should_notify_manager(gpt_answer):
            await notify_manager(
                context,
                f"📞 Клиент оставил контакт\n{user.id}\n{text}\n{gpt_answer}"
            )

        # --- ответ ---
        await update.message.reply_text(gpt_answer)

    except Exception as e:
        logger.error(f"Ошибка handle_gpt_query: {e}", exc_info=True)

        try:
            await update.message.reply_text("🔧 Ошибка обработки запроса")
        except:
            pass


# =======================
# 🔹 Очередь админов
# =======================

async def process_admin_queue(app: Application):
    for admin_id, messages in list(ADMIN_QUEUE.items()):
        if not messages:
            continue

        try:
            await app.bot.send_message(
                chat_id=admin_id,
                text="🔔 Пропущенные уведомления:\n" + "\n".join(messages)
            )
            ADMIN_QUEUE[admin_id] = []
        except Exception:
            continue
