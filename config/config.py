# config.py

import os
import logging
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

from telegram import (
    ReplyKeyboardRemove
)

logger = logging.getLogger(__name__)


# =======================
# 🔹 ENV
# =======================

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(env_path)


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

def get_empty_keyboard():
    return ReplyKeyboardRemove()


# =======================
# 🔹 АДМИНЫ
# =======================

def is_admin(user_id: int) -> bool:
    from database_old import is_admin as db_is_admin, DB_PATH
    return user_id == SUPERADMIN_ID or db_is_admin(DB_PATH, user_id)
