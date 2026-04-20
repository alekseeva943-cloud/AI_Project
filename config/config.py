# config.py

import os
import logging
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

logger = logging.getLogger(__name__)


# =======================
# 🔹 ENV
# =======================

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class ConfigError(Exception):
    pass


def validate_env_vars():
    required = [
        "TELEGRAM_TOKEN",
        "OPENAI_API_KEY",
        "MANAGER_CHAT_ID",
        "SUPERADMIN_ID"
    ]

    missing = [v for v in required if not os.getenv(v)]

    if missing:
        raise ConfigError(f"Нет переменных: {', '.join(missing)}")


try:
    validate_env_vars()

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))
    SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID"))

except Exception as e:
    logger.critical(f"Ошибка config: {e}")
    raise


# =======================
# 🔹 НАСТРОЙКИ
# =======================

# 🔥 сколько сообщений передаём в GPT
CONTEXT_MESSAGE_COUNT = 20

# 🔥 очередь админов
ADMIN_QUEUE = defaultdict(list)


# =======================
# 🔹 КЛАВИАТУРЫ
# =======================

def get_main_keyboard(is_admin_user: bool = False):
    keyboard = [
        [KeyboardButton("🆘 Нужна помощь")],
        [
            KeyboardButton("📞 Оставить телефон", request_contact=True),
            KeyboardButton("📍 Отправить локацию", request_location=True)
        ],
        [
            KeyboardButton("🛠 Наши услуги"),
            KeyboardButton("📱 Наши контакты")
        ]
    ]

    if is_admin_user:
        keyboard.insert(0, [KeyboardButton("🛠 Админка")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["📢 Рассылка", "🔍 Поиск клиентов"],
            ["📊 Статистика", "📈 Топ запросов"],
            ["⚙️ Настройки", "👥 Пользователи"],
            ["⬅️ Вернуться"]
        ],
        resize_keyboard=True
    )


def get_settings_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["👥 Админы"],
            ["⬅️ Назад"]
        ],
        resize_keyboard=True
    )


def get_admins_management_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            ["➕ Добавить админа", "🗑 Удалить админа"],
            ["⬅️ Назад"]
        ],
        resize_keyboard=True
    )


def get_empty_keyboard():
    return ReplyKeyboardRemove()


# =======================
# 🔹 АДМИНЫ
# =======================

def is_admin(user_id: int) -> bool:
    from database import is_admin as db_is_admin, DB_PATH
    return user_id == SUPERADMIN_ID or db_is_admin(DB_PATH, user_id)
