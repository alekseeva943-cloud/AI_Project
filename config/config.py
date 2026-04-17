# config.py

import os
import logging
import json
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логгера
logger = logging.getLogger(__name__)

# Загрузка .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Настройки контекста
CONTEXT_MESSAGE_COUNT = 10  # Количество сообщений, отправляемых менеджеру
UNCERTAIN_MESSAGE = "Уточняю информацию...\n\n"


class ConfigError(Exception):
    """Кастомное исключение для ошибок конфигурации"""
    pass


def validate_env_vars() -> None:
    """Проверка обязательных переменных окружения"""
    required_vars = {
        'TELEGRAM_TOKEN': 'Токен бота Telegram',
        'OPENAI_API_KEY': 'Ключ OpenAI API',
        'MANAGER_CHAT_ID': 'ID чата менеджера',
        'SUPERADMIN_ID': 'ID главного администратора'
    }
    missing_vars = [name for name in required_vars if not os.getenv(name)]
    if missing_vars:
        raise ConfigError(f"Отсутствуют переменные: {', '.join(missing_vars)}")


# Загрузка и валидация основных настроек
try:
    validate_env_vars()

    TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
    MANAGER_CHAT_ID = int(os.environ["MANAGER_CHAT_ID"])
    SUPERADMIN_ID = int(os.environ["SUPERADMIN_ID"])

except (ConfigError, ValueError, KeyError) as e:
    logger.critical(f"Ошибка загрузки конфигурации: {e}")
    raise


# Пути к файлам
PROMPT_CONFIG_PATH = Path(__file__).parent / "gpt_prompt.json"
# Настройки таймаутов
GPT_TIMEOUT = int(os.getenv("GPT_TIMEOUT", "120"))  # По умолчанию 120 секунд
# Загрузка тематических промтов
PROMPT_TEMPLATES_PATH = Path(__file__).parent / "prompt_templates.json"

try:
    with open(PROMPT_TEMPLATES_PATH, "r", encoding="utf-8") as f:
        PROMPT_TEMPLATES = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.warning(
        f"Не удалось загрузить prompt_templates.json — используются дефолтные значения")
    PROMPT_TEMPLATES = {
        "tire": "Ты эксперт по шиномонтажу...",
        "ac": "Ты специалист по авто-кондиционерам...",
        "other": "Ты консультант по дополнительным услугам...",
        "contacts": "📍 Наши контакты:\n..."
    }


# Загрузка промтов и настроек GPT
try:
    with open(PROMPT_CONFIG_PATH, "r", encoding="utf-8") as f:
        prompt_config = json.load(f)

    # Берём всё из JSON
    SYSTEM_PROMPT = prompt_config.get("system_prompt", "")
    GPT_MODEL = prompt_config.get("model", "gpt-3.5-turbo")
    GPT_TEMPERATURE = float(prompt_config.get("temperature", 0.7))
    GPT_MAX_TOKENS = int(prompt_config.get("max_tokens", 100))

    # Резервные значения, если не задано в JSON
    if not SYSTEM_PROMPT:
        SYSTEM_PROMPT = """
Ты консультант компании Professional24 (выездной шиномонтаж). 
Отвечай как живой менеджер: дружелюбно, но профессионально. 
Не упоминай, что ты ИИ. Если не знаешь ответа, скажи: "Минуту, уточню детали..."
""".strip()
        logger.warning(
            "SYSTEM_PROMPT не найден в gpt_prompt.json — используется стандартный")

except (FileNotFoundError, json.JSONDecodeError) as e:
    logger.warning(
        f"Не удалось загрузить gpt_prompt.json, используются дефолтные значения: {e}")

    # Дефолтные значения, если JSON отсутствует
    SYSTEM_PROMPT = """
Ты консультант компании Professional24 (выездной шиномонтаж). 
Отвечай как живой менеджер: дружелюбно, но профессионально. 
Не упоминай, что ты ИИ. Если не знаешь ответа, скажи: "Минуту, уточню детали..."
""".strip()
    GPT_MODEL = "gpt-4o-mini"
    GPT_TEMPERATURE = 0.7
    GPT_MAX_TOKENS = 100


# Таймаут для GPT (в секундах)
GPT_TIMEOUT = 120


# Очередь для админов
ADMIN_QUEUE = defaultdict(list)


async def process_admin_queue(app):
    """Отправка накопленных сообщений админам"""
    try:
        for admin_id, messages in list(ADMIN_QUEUE.items()):
            if messages:
                try:
                    await app.bot.send_message(
                        chat_id=admin_id,
                        text="🔔 Накопившиеся уведомления:\n" +
                        "\n\n".join(messages)
                    )
                    ADMIN_QUEUE[admin_id] = []
                except Exception as e:
                    logger.error(f"Ошибка отправки админу {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка обработки очереди: {e}")


# Шаблоны промптов по темам
# PROMPT_TEMPLATES = {
 #   "tire": "Ты эксперт по шиномонтажу...",
  #  "ac": "Ты специалист по авто-кондиционерам...",
   # "other": "Ты консультант по дополнительным услугам...",
    # "contacts": "📍 Наши контакты:\n..."
# }


# Функции клавиатур

def get_main_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🆘 Нужна помощь")],
        [
            KeyboardButton("📞 Оставить телефон", request_contact=True),
            KeyboardButton("📍 Отправить локацию", request_location=True)
        ],
        [KeyboardButton("🛠 Наши услуги"), KeyboardButton("📱 Наши контакты")]
    ]

    if is_admin_user:
        keyboard.insert(0, [KeyboardButton("🛠 Админка")])  # Вставляем в начало

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для админ-панели"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📢 Рассылка"), KeyboardButton("🔍 Поиск клиентов")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("📈 Топ запросов")],
            [KeyboardButton("⚙️ Настройки"), KeyboardButton(
                "👥 Пользователи")],
            [KeyboardButton("⬅️ Вернуться")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_empty_keyboard() -> ReplyKeyboardRemove:
    """Удаление клавиатуры"""
    return ReplyKeyboardRemove()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора — временно через SUPERADMIN_ID + БД (заглушка)"""
    from database import is_admin as db_is_admin, DB_PATH
    return user_id == SUPERADMIN_ID or db_is_admin(DB_PATH, user_id)


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура подменю 'Настройки'"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("👥 Админы")],
            [KeyboardButton("⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_admins_management_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("➕ Добавить админа"),
             KeyboardButton("🗑 Удалить админа")],
            [KeyboardButton("⬅️ Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


if __name__ == "__main__":
    print("\nКонфигурация успешно загружена:")
    print(f"Главный админ (SUPERADMIN_ID): {SUPERADMIN_ID}")
    print(f"Модель GPT: {GPT_MODEL}")
    print("=" * 40)
