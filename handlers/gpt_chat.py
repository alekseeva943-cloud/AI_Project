# handlers/gpt_chat.py

"""
Обработка GPT-диалога.

Назначение:
- обработка сообщений пользователя;
- определение намерения (Router);
- поиск информации через RAG;
- генерация ответа GPT;
- обработка лидов;
- уведомление администраторов.
"""

import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
)

from config.config import (
    ADMIN_QUEUE,
    CONTEXT_MESSAGE_COUNT,
)

from database import (
    DB_PATH,
    add_message,
    get_all_admins,
    get_client_info,
    get_last_messages,
    save_client_info,
)

from handlers.start import start as main_menu_handler
from services.gpt_service import generate_answer
from services.rag_service import retrieve_context
from services.router_service import classify_intent


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Константы модуля.
# ==========================================================

# Сообщение пользователю после
# успешной отправки заявки менеджеру.
CLIENT_LEAD_RESPONSE = (
    "Отправил ваши контакты бригаде 🚗\n"
    "С вами скоро свяжутся "
    "и подъедут на место 👍"
)

# Заголовок новой заявки,
# отображаемый у администратора.
ADMIN_NEW_LEAD_TITLE = (
    "📞 НОВАЯ ЗАЯВКА"
)


# ==========================================================
# Вспомогательные функции.
# ==========================================================

def is_phone(text: str) -> bool:
    """
    Проверяет, содержит ли строка
    номер телефона.

    Returns:
        bool.
    """

    digits = re.sub(
        r"\D",
        "",
        text,
    )

    return len(digits) >= 10

# ==========================================================
# Работа с историей диалога.
# ==========================================================

def format_history(
    history: list,
) -> str:
    """
    Преобразует историю диалога
    в удобный текстовый формат
    для администратора.

    Returns:
        str.
    """

    lines = []

    for message in history[-10:]:

        role = (
            "👤 Клиент"
            if message["role"] == "user"
            else "🤖 Бот"
        )

        lines.append(
            f"{role}: {message['content']}"
        )

    return "\n".join(lines)


def append_if_not_duplicate(
    history: list,
    text: str,
) -> list:
    """
    Добавляет сообщение
    в историю только при отсутствии
    полного совпадения с последним.

    Returns:
        list.
    """

    if (
        history
        and history[-1]["role"] == "user"
        and history[-1]["content"] == text
    ):
        return history

    return history + [
        {
            "role": "user",
            "content": text,
        }
    ]

# ==========================================================
# Уведомление администраторов.
# ==========================================================

async def notify_manager(
    context: ContextTypes.DEFAULT_TYPE,
    message: str,
):
    """
    Отправляет новую заявку
    всем администраторам.

    Если сообщение не удалось
    отправить, оно помещается
    в очередь повторной отправки.

    Returns:
        None.
    """

    admins = get_all_admins(DB_PATH)

    for admin in admins:

        try:

            await context.bot.send_message(
                chat_id=admin["user_id"],
                text=message,
            )

        except Exception:

            ADMIN_QUEUE.setdefault(
                admin["user_id"],
                [],
            ).append(message)

# ==========================================================
# Формирование заявки.
# ==========================================================

def build_lead_message(
    user,
    text: str,
    history: list,
) -> str:
    """
    Формирует карточку заявки
    для администратора.

    В карточку входят:
    - данные пользователя;
    - телефон;
    - последнее действие;
    - история переписки.

    Returns:
        str.
    """

    # Формируем отображаемый username.
    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    # Получаем историю переписки.
    context_text = format_history(history)

    # Получаем сохранённые данные клиента.
    client_info = get_client_info(user.id)

    # Добавляем телефон,
    # если он уже известен системе.
    phone = (
        client_info.get("phone")
        if client_info
        and client_info.get("phone")
        else "не указан"
    )

    return (
        f"{ADMIN_NEW_LEAD_TITLE}\n\n"
        f"👤 {username}\n"
        f"🆔 {user.id}\n"
        f"🔗 tg://user?id={user.id}\n"
        f"📞 {phone}\n\n"
        f"📩 Последнее действие:\n"
        f"{text}\n\n"
        f"📄 История диалога:\n"
        f"{context_text}"
    )


# ==========================================================
# Основной обработчик GPT.
# ==========================================================

async def handle_gpt_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Обрабатывает сообщения пользователя,
    определяет намерение, при необходимости
    обращается к RAG и GPT, а также
    формирует заявки для менеджеров.

    Returns:
        None.
    """

    try:

        user = update.effective_user
        message = update.message

        if not message:
            return

        text = message.text or ""

        # ----------------------------------------------
        # Игнорируем команды и кнопки,
        # которые не должны обрабатываться GPT.
        # ----------------------------------------------

        if (
            text.startswith("/")
            or text == "💬 Задать вопрос"
        ):
            return

        if text == "⬅️ Вернуться":
            await main_menu_handler(
                update,
                context,
            )
            return

        # ----------------------------------------------
        # Обновляем информацию о пользователе.
        # ----------------------------------------------

        client_info = get_client_info(user.id)

        phone_saved = (
            client_info.get("phone")
            if client_info
            else None
        )

        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=phone_saved,
        )

        # ----------------------------------------------
        # Загружаем историю диалога.
        # ----------------------------------------------

        history = get_last_messages(
            user.id,
            db_path=DB_PATH,
            limit=CONTEXT_MESSAGE_COUNT,
        )

        # ==================================================
        # Обработка номера телефона.
        # ==================================================

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
                phone=phone,
            )

            full_history = append_if_not_duplicate(
                history,
                text,
            )

            manager_message = build_lead_message(
                user,
                f"📞 Телефон: {phone}",
                full_history,
            )

            await notify_manager(
                context,
                manager_message,
            )

            await message.reply_text(
                CLIENT_LEAD_RESPONSE,
            )

            context.user_data["lead_sent"] = True

            return

        # ==================================================
        # Обработка геолокации.
        # ==================================================

        if message.location:

            latitude = message.location.latitude
            longitude = message.location.longitude

            full_history = append_if_not_duplicate(
                history,
                f"📍 Геолокация: "
                f"{latitude}, {longitude}",
            )

            manager_message = build_lead_message(
                user,
                "📍 Клиент отправил геолокацию",
                full_history,
            )

            await notify_manager(
                context,
                manager_message,
            )

            for admin in get_all_admins(DB_PATH):

                try:

                    await context.bot.send_location(
                        chat_id=admin["user_id"],
                        latitude=latitude,
                        longitude=longitude,
                    )

                except Exception as error:

                    logger.error(
                        "Ошибка отправки "
                        f"геолокации админу "
                        f"{admin['user_id']}: {error}"
                    )

            await message.reply_text(
                "✅ Геолокация получена.\n\n"
                "🚗 Ближайшая бригада уже "
                "получила адрес и выехала "
                "к вам.\n\n"
                "📞 При необходимости "
                "менеджер свяжется с вами "
                "для уточнения деталей."
            )

            context.user_data["lead_sent"] = True

            return
        
        # ==================================================
        # Сохраняем сообщение пользователя.
        # ==================================================

        add_message(
            user.id,
            "user",
            text,
        )

        history = get_last_messages(
            user.id,
            db_path=DB_PATH,
            limit=CONTEXT_MESSAGE_COUNT,
        )

        # ==================================================
        # Определяем намерение пользователя.
        # ==================================================

        intent_data = classify_intent(
            text,
            history,
        )

        intent = intent_data.get(
            "intent",
            "unknown",
        )

        logger.info(
            f"[ROUTER] intent={intent} text={text}"
        )

        # ==================================================
        # Получаем контекст из RAG.
        # ==================================================

        context_data = None

        if intent in (
            "problem",
            "info",
        ):
            context_data = retrieve_context(
                text,
            )

        # ==================================================
        # Генерируем ответ GPT.
        # ==================================================

        answer = generate_answer(
            query=text,
            history=history,
            context=context_data,
        )

        if not answer:
            answer = (
                "Можете чуть подробнее "
                "описать ситуацию 👍"
            )

        add_message(
            user.id,
            "assistant",
            answer,
        )

        await message.reply_text(
            answer,
        )

        # ==================================================
        # Отправляем заявку менеджеру,
        # если Router определил лид.
        # ==================================================

        if (
            intent == "lead"
            and not context.user_data.get(
                "lead_sent"
            )
        ):

            full_history = get_last_messages(
                user.id,
                db_path=DB_PATH,
                limit=CONTEXT_MESSAGE_COUNT,
            )

            manager_message = build_lead_message(
                user,
                text,
                full_history,
            )

            await notify_manager(
                context,
                manager_message,
            )

            context.user_data[
                "lead_sent"
            ] = True

    except Exception as error:

        logger.exception(
            f"Ошибка handle_gpt_query: "
            f"{error}"
        )

        try:

            await update.message.reply_text(
                "🔧 Ошибка обработки запроса"
            )

        except Exception:
            pass

# ==========================================================
# Отправка отложенных уведомлений.
# ==========================================================

async def process_admin_queue(
    app: Application,
):
    """
    Отправляет администраторам
    сообщения, которые ранее
    не удалось доставить.

    Returns:
        None.
    """

    for admin_id, messages in list(
        ADMIN_QUEUE.items()
    ):

        if not messages:
            continue

        try:

            await app.bot.send_message(
                chat_id=admin_id,
                text=(
                    "🔔 Пропущенные уведомления:\n"
                    + "\n".join(messages)
                ),
            )

            ADMIN_QUEUE[admin_id] = []

        except Exception:

            continue