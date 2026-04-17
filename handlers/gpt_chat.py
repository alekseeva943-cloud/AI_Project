# Стандартная библиотека
import asyncio
import logging
from collections import deque
from pathlib import Path
import json

# Внешние библиотеки
from openai import OpenAI
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, User
from telegram.ext import ContextTypes, Application, MessageHandler, filters

# Локальные модули проекта
from config.config import (

    ADMIN_QUEUE,
    SYSTEM_PROMPT,
    PROMPT_TEMPLATES,
    GPT_MODEL,
    GPT_TEMPERATURE,
    GPT_MAX_TOKENS,
    OPENAI_API_KEY,
    CONTEXT_MESSAGE_COUNT,
    UNCERTAIN_MESSAGE,
    GPT_TIMEOUT
)
from database import (
    save_client_info,
    add_message,
    get_last_messages,
    DB_PATH,
    get_client_info,
    has_client_phone  # Добавляем, если используется
)
from handlers.admin_utils import send_context_to_admin
from handlers.start import start as main_menu_handler  # Главное меню
from handlers.utilities import show_auto_help_submenu  # Подменю авто-помощи

# Настройка логгирования
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Путь к шаблонам промтов
PROMPT_TEMPLATES_PATH = Path("config/prompt_templates.json")


def load_prompt_templates():
    logger.info(
        f"Попытка загрузить prompt-шаблоны из: {PROMPT_TEMPLATES_PATH.absolute()}")
    try:
        with open(PROMPT_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки prompt-шаблонов: {e}")
        return {}


PROMPT_TEMPLATES = load_prompt_templates()

logger.info(
    f"[load_prompt_templates] Загружено {len(PROMPT_TEMPLATES)} шаблонов")
logger.info(f"[load_prompt_templates] Ключи: {list(PROMPT_TEMPLATES.keys())}")

# Временная история (не используется напрямую, если уже используем БД)
CHAT_HISTORY = deque(maxlen=10)


def is_uncertain_response(text: str) -> bool:
    """Проверяет, является ли ответ GPT неуверенным"""
    uncertain_triggers = ["не знаю", "не уверен", "уточните",
                          "думаю", "предположительно", "скорее всего"]
    return any(trigger in text.lower() for trigger in uncertain_triggers)


def should_notify_manager(text: str) -> bool:
    """Проверяет, нужно ли уведомить менеджера о контакте/адресе"""
    contact_triggers = [
        "передам", "менеджеру", "свяжемся", "свяжется",
        "перезвонит", "номер принят",
        "мы вам позвоним", "мы перезвоним", "ожидайте"
    ]
    return any(trigger.lower() in text.lower() for trigger in contact_triggers)


async def show_service_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает описание услуги из services.json"""
    service = update.message.text
    try:
        with open("config/services.json", "r", encoding="utf-8") as f:
            descriptions = json.load(f)
    except Exception as e:
        logger.error(f"Не удалось загрузить services.json: {e}")
        return

    description = descriptions.get(service)
    if not description:
        return  # Неизвестная кнопка

    if service == "⬅️ Вернуться":
        await main_menu_handler(update, context)
        return

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True
    )
    await update.message.reply_text(description, reply_markup=reply_markup, parse_mode="Markdown")


async def notify_manager(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Уведомляет всех админов из базы данных; при ошибке — добавляет в очередь"""
    try:
        from database import get_all_admins, DB_PATH
        from config import ADMIN_QUEUE
        import logging
        logger = logging.getLogger(__name__)

        admins = get_all_admins(DB_PATH)
        for admin in admins:
            admin_id = admin['user_id']
            try:
                await context.bot.send_message(chat_id=admin_id, text=message)
            except Exception as send_error:
                # Добавляем в очередь для последующей отправки
                if admin_id not in ADMIN_QUEUE:
                    ADMIN_QUEUE[admin_id] = []
                ADMIN_QUEUE[admin_id].append(message)
                logger.warning(
                    f"Не удалось отправить сообщение админу {admin_id}: {send_error}. Добавлено в очередь.")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(
            f"Критическая ошибка в notify_manager: {e}", exc_info=True)


async def handle_services_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку '🛠 Наши услуги'"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} выбрал 'Наши услуги'")
    from handlers.utilities import handle_services
    await handle_services(update, context)


async def show_auto_help_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает описание выбранной услуги авто-помощи или контакты"""
    user = update.effective_user
    service = update.message.text
    logger.info(f"[show_auto_help_details] Получено: {service}")

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True
    )

    if service == "⬅️ Вернуться":
        await main_menu_handler(update, context)
        return

    try:
        with open("config/services.json", "r", encoding="utf-8") as f:
            descriptions = json.load(f)
    except Exception as e:
        logger.error(f"Не удалось загрузить services.json: {e}")
        await update.message.reply_text("❌ Ошибка загрузки данных.")
        return

    description = descriptions.get(service)
    if not description:
        logger.warning(f"Неизвестная услуга: {service}")
        return

    # Сохраняем тему в контексте для последующего использования ("подробнее")
    context.user_data['last_service'] = service
    # Сохраняем факт выбора темы в базу
    add_message(user.id, "user", f"Информация о: {service}")

    # Показываем описание
    await update.message.reply_text(description, reply_markup=reply_markup, parse_mode="Markdown")


async def handle_gpt_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений GPT с контекстом и отправкой админу при неуверенности"""
    # 🔍 DEBUG: первое, что видим — дошла ли функция до вызова
    try:
        user = update.effective_user
        user_message = update.message.text
        logger.info(
            f"[DEBUG] handle_gpt_query вызван: '{user_message}' от @{user.username} (ID: {user.id})")
    except Exception as e:
        logger.error(
            f"[CRITICAL] Ошибка при разборе update в handle_gpt_query: {e}", exc_info=True)
        return

    try:
        # Пропускаем команды и стандартные кнопки
        if user_message.startswith('/') or user_message in ["💬 Задать вопрос"]:
            logger.debug(
                "Сообщение проигнорировано: команда или кнопка 'Задать вопрос'")
            return

        # Обработка кнопки "Вернуться"
        if user_message == "⬅️ Вернуться":
            await main_menu_handler(update, context)
            return

        # --- Получаем текущую информацию о клиенте ---
        # Используем глобальный импорт из начала файла
        client_info = get_client_info(user.id)
        phone = client_info.get('phone') if client_info else None

        # --- Обработка фиксированных тем из "Наши услуги" ---
        topic_mapping = {
            "🛞 Шиномонтаж": "tire",
            "❄️ Кондиционер": "ac",
            "🔧 Другие услуги": "other",
            "📍 Контакты": "contacts"
        }

        help_topic_mapping = {
            "🛞 Спустило колесо": "flat_tire",
            "⛽ Нет топлива": "fuel_delivery",
            "🚗 Не заводится": "engine_start",
            "❄️ Отогреть": "winter_help",
            "🌬 Кондиционер": "ac",
            "⚡ Электрика": "electrics",
            "🔓 Вскрыть": "unlock",
            "💻 Диагностика": "diagnostics",
            "❓ Прочее": "other_help"
        }

        # --- Обработка фиксированных тем ---
        if user_message in topic_mapping:
            template_key = topic_mapping[user_message]
            system_prompt = PROMPT_TEMPLATES.get(template_key, SYSTEM_PROMPT)
            context.user_data['system_prompt'] = system_prompt

            if template_key in ["contacts", "other"]:
                await show_auto_help_details(update, context)
                return

            initial_question = {
                "tire": "Какие услуги по шиномонтажу вы предоставляете?",
                "ac": "Расскажите о сервисе автокондиционеров.",
                "other": "Какие дополнительные услуги вы предлагаете?"
            }.get(template_key, "Задайте ваш вопрос.")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": initial_question}
            ]

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.chat.completions.create,
                        model=GPT_MODEL,
                        messages=messages,
                        temperature=GPT_TEMPERATURE,
                        max_tokens=GPT_MAX_TOKENS
                    ),
                    timeout=GPT_TIMEOUT
                )
                gpt_answer = response.choices[0].message.content
            except asyncio.TimeoutError:
                gpt_answer = "⚠️ Уточните, пожалуйста, вопрос"
                logger.warning("Таймаут GPT")
            except Exception as e:
                gpt_answer = "🔧 Ошибка сервиса"
                logger.error(f"Ошибка GPT: {type(e).__name__}", exc_info=True)

            save_client_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=phone
            )

            add_message(user.id, "user", initial_question)

            if gpt_answer and gpt_answer.strip():
                add_message(user.id, "assistant", gpt_answer)

            reply_markup = ReplyKeyboardMarkup(
                [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True
            )
            await update.message.reply_text(gpt_answer, reply_markup=reply_markup)
            return

        # --- Обработка тем из "Нужна помощь" ---
        if user_message in help_topic_mapping:
            template_key = help_topic_mapping[user_message]
            system_prompt = PROMPT_TEMPLATES.get(template_key, SYSTEM_PROMPT)
            context.user_data['system_prompt'] = system_prompt
            context.user_data['help_topic'] = user_message

            initial_question = {
                "flat_tire": "Мне спустило колесо, что делать?",
                "fuel_delivery": "Закончилось топливо, сможете доставить?",
                "engine_start": "Не могу завести машину, помогите!",
                "winter_help": "Машина не заводится из-за мороза, что делать?",
                "electrics": "Проблемы с проводкой или аккумулятором, что предлагаете?",
                "unlock": "Заблокировался в машине / забыл ключи, поможете?",
                "diagnostics": "Хочу сделать диагностику перед поездкой, что входит?",
                "other_help": "Опишите вашу ситуацию."
            }.get(template_key, "Задайте ваш вопрос.")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": initial_question}
            ]

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.chat.completions.create,
                        model=GPT_MODEL,
                        messages=messages,
                        temperature=GPT_TEMPERATURE,
                        max_tokens=GPT_MAX_TOKENS
                    ),
                    timeout=GPT_TIMEOUT
                )
                gpt_answer = response.choices[0].message.content
            except asyncio.TimeoutError:
                gpt_answer = "⚠️ Уточните, пожалуйста, вопрос"
                logger.warning("Таймаут GPT")
            except Exception as e:
                gpt_answer = "🔧 Ошибка сервиса"
                logger.error(f"Ошибка GPT: {type(e).__name__}", exc_info=True)

            save_client_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=phone
            )

            add_message(user.id, "user", initial_question)

            if gpt_answer and gpt_answer.strip():
                add_message(user.id, "assistant", gpt_answer)

            reply_markup = ReplyKeyboardMarkup(
                [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True
            )
            await update.message.reply_text(gpt_answer, reply_markup=reply_markup)
            return

        # --- Основной случай: пользователь пишет свой текст ---
        logger.info(
            f"Обработка свободного запроса от @{user.username} (ID: {user.id})")

        save_client_info(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=phone
        )

        add_message(user.id, "user", user_message)
        logger.debug(
            f"[{user.id}] Сообщение пользователя сохранено: {user_message[:50]}...")

        db_history = get_last_messages(
            user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT)
        logger.debug(
            f"[{user.id}] Загружено {len(db_history)} сообщений из БД")

        # Получаем текущий системный промпт
        help_topic = context.user_data.get('help_topic')
        system_content = context.user_data.get('system_prompt', SYSTEM_PROMPT)

        if help_topic:
            system_content = f"Пользователь выбрал: {help_topic}\n{system_content}"

        messages = [
            {"role": "system", "content": system_content},
            *db_history,
            {"role": "user", "content": user_message}
        ]

        await update.message.reply_chat_action("typing")
        logger.info(
            f"[handle_gpt_query] system_content = {system_content[:100]}...")

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model=GPT_MODEL,
                    messages=messages,
                    temperature=GPT_TEMPERATURE,
                    max_tokens=GPT_MAX_TOKENS
                ),
                timeout=GPT_TIMEOUT
            )
            gpt_answer = response.choices[0].message.content
        except asyncio.TimeoutError:
            gpt_answer = "⚠️ Уточните, пожалуйста, вопрос"
            logger.warning("Таймаут GPT")
        except Exception as e:
            gpt_answer = "🔧 Ошибка сервиса"
            logger.error(f"Ошибка GPT: {type(e).__name__}", exc_info=True)

        if gpt_answer and gpt_answer.strip():
            add_message(user.id, "assistant", gpt_answer)
            logger.debug(
                f"[{user.id}] Ответ GPT сохранён: {gpt_answer[:50]}...")
        else:
            logger.warning(f"[{user.id}] GPT вернул пустой ответ")

        if is_uncertain_response(gpt_answer):
            logger.warning(
                f"[{user.id}] ❗ Неуверенный ответ от GPT:\n{gpt_answer[:200]}...")

            last_messages = get_last_messages(
                user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT)
            context_text = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in last_messages])

            username = f"@{user.username}" if user.username else "без логина"

            uncertain_msg = (
                f"⚠️ Неуверенный запрос ({username}, ID: {user.id}):\n"
                f"Вопрос клиента: {user_message}\n"
                f"GPT: {gpt_answer}\n"
                f"📄 Последний контекст ({len(last_messages)} сообщений):\n"
                f"{context_text if context_text else 'нет истории'}\n"
                f"🔗 tg://user?id={user.id}"
            )

            await notify_manager(update, context, uncertain_msg)

        if should_notify_manager(gpt_answer):
            logger.info(f"[{user.id}] 📞 Ответ содержит контактную информацию")

            last_messages = get_last_messages(
                user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT)
            context_text = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in last_messages])

            username = f"@{user.username}" if user.username else "без логина"

            contact_msg = (
                f"📞 Клиент оставил контактную информацию ({username}, ID: {user.id})\n"
                f"Вопрос клиента: {user_message}\n"
                f"GPT: {gpt_answer}\n"
                f"📄 Последний контекст ({len(last_messages)} сообщений):\n"
                f"{context_text if context_text else 'нет истории'}\n"
                f"🔗 tg://user?id={user.id}"
            )

            await notify_manager(update, context, contact_msg)

        await update.message.reply_text(gpt_answer)

    except Exception as e:
        logger.error(
            f"Критическая ошибка в handle_gpt_query: {type(e).__name__}", exc_info=True)
        try:
            await update.message.reply_text("🔧 Произошла ошибка при обработке запроса.")
        except Exception:
            pass  # если даже ответить нельзя — молчим
        try:
            await notify_manager(update, context, f"🚨 Ошибка у @{user.username} (ID: {user.id})")
        except Exception:
            pass


async def process_admin_queue(app: Application):
    """Отправка сообщений из очереди администраторам"""
    try:
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
    except Exception as e:
        logger.error(f"Ошибка обработки очереди: {e}")
