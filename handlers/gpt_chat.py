# gpt_chat.py

import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, Application

from config.config import ADMIN_QUEUE, CONTEXT_MESSAGE_COUNT

from database import (
    save_client_info,
    add_message,
    get_last_messages,
    DB_PATH,
    get_client_info
)

from handlers.start import start as main_menu_handler
from services.router_service import classify_intent
from services.rag_service import retrieve_context
from services.gpt_service import generate_answer

logger = logging.getLogger(__name__)


# =======================
# 🔹 КОНСТАНТЫ (ВСЁ В ОДНОМ МЕСТЕ)
# =======================

CLIENT_LEAD_RESPONSE = (
    "Отправил ваши контакты бригаде 🚗\n"
    "С вами скоро свяжутся и подъедут на место 👍"
)

ADMIN_NEW_LEAD_TITLE = "📞 НОВАЯ ЗАЯВКА"


# =======================
# 🔹 УТИЛИТЫ
# =======================

def is_phone(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return len(digits) >= 10


def format_history(history: list) -> str:
    lines = []
    for msg in history[-10:]:
        role = "👤 Клиент" if msg["role"] == "user" else "🤖 Бот"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def append_if_not_duplicate(history: list, text: str) -> list:
    if history and history[-1]["role"] == "user" and history[-1]["content"] == text:
        return history
    return history + [{"role": "user", "content": text}]


# =======================
# 🔹 УВЕДОМЛЕНИЕ АДМИНА
# =======================

async def notify_manager(context: ContextTypes.DEFAULT_TYPE, message: str):
    from database import get_all_admins

    admins = get_all_admins(DB_PATH)

    for admin in admins:
        try:
            await context.bot.send_message(
                chat_id=admin["user_id"],
                text=message
            )
        except Exception:
            ADMIN_QUEUE.setdefault(admin["user_id"], []).append(message)


# =======================
# 🔹 СБОРКА ЗАЯВКИ
# =======================

def build_lead_message(user, text: str, history: list) -> str:
    username = f"@{user.username}" if user.username else "без username"
    context_text = format_history(history)

    return f"""
{ADMIN_NEW_LEAD_TITLE}

👤 {username}
🆔 {user.id}
🔗 tg://user?id={user.id}

📩 Последнее сообщение:
{text}

📄 Диалог:
{context_text}
"""


# =======================
# 🔹 ОСНОВНОЙ HANDLER
# =======================

async def handle_gpt_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        message = update.message

        if not message:
            return

        text = message.text or ""

        # --- фильтры ---
        if text.startswith("/") or text == "💬 Задать вопрос":
            return

        if text == "⬅️ Вернуться":
            await main_menu_handler(update, context)
            return

        # --- сохраняем клиента ---
        client_info = get_client_info(user.id)
        phone_saved = client_info.get("phone") if client_info else None

        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=phone_saved
        )

        # --- история ДО ---
        history = get_last_messages(
            user.id,
            db_path=DB_PATH,
            limit=CONTEXT_MESSAGE_COUNT
        )

        # =======================
        # 🔥 ТЕЛЕФОН
        # =======================

        phone = None

        if message.contact:
            phone = message.contact.phone_number
        elif is_phone(text):
            phone = text

        if phone:
            save_client_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=phone
            )

            full_history = append_if_not_duplicate(history, text)

            msg = build_lead_message(
                user,
                f"📞 Телефон: {phone}",
                full_history
            )

            await notify_manager(context, msg)
            await message.reply_text(CLIENT_LEAD_RESPONSE)

            context.user_data["lead_sent"] = True
            return

        # =======================
        # 🔥 СОХРАНЯЕМ СООБЩЕНИЕ
        # =======================

        add_message(user.id, "user", text)

        history = get_last_messages(
            user.id,
            db_path=DB_PATH,
            limit=CONTEXT_MESSAGE_COUNT
        )

        # =======================
        # 🔥 ROUTER
        # =======================

        intent_data = classify_intent(text, history)
        intent = intent_data.get("intent", "unknown")

        logger.info(f"[ROUTER] intent={intent} text={text}")

        # =======================
        # 🔥 RAG
        # =======================

        context_data = None

        if intent in ["problem", "info"]:
            context_data = retrieve_context(text)

        # =======================
        # 🔥 GPT
        # =======================

        answer = generate_answer(
            query=text,
            history=history,
            context=context_data
        )

        # =======================
        # 🔥 LEAD (ОДИН РАЗ)
        # =======================

        if intent == "lead" and not context.user_data.get("lead_sent"):

            full_history = append_if_not_duplicate(history, text)

            msg = build_lead_message(user, text, full_history)

            await notify_manager(context, msg)
            context.user_data["lead_sent"] = True

        # =======================
        # 🔹 FALLBACK
        # =======================

        if not answer:
            answer = "Можете чуть подробнее описать ситуацию 👍"

        add_message(user.id, "assistant", answer)
        await message.reply_text(answer)

    except Exception as e:
        logger.error(f"Ошибка handle_gpt_query: {e}", exc_info=True)

        try:
            await update.message.reply_text("🔧 Ошибка обработки запроса")
        except Exception:
            pass


# =======================
# 🔹 ОЧЕРЕДЬ
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