# config/_init_.py

from .config import (
    TELEGRAM_TOKEN,
    OPENAI_API_KEY,
    MANAGER_CHAT_ID,
    GPT_MODEL,
    GPT_MAX_TOKENS,
    GPT_TEMPERATURE,
    SYSTEM_PROMPT,
    SUPERADMIN_ID,
    get_main_keyboard,
    get_admin_keyboard,
    get_admins_management_keyboard,
    is_admin,
    ADMIN_QUEUE  # Добавлено
)
from .config import process_admin_queue

# Для обратной совместимости (если где-то используется прямое обращение)
from .config import (
    TELEGRAM_TOKEN as TOKEN,
    OPENAI_API_KEY as OPENAI_KEY,
    MANAGER_CHAT_ID as MANAGER_ID,
)

__all__ = [
    'TELEGRAM_TOKEN',
    'OPENAI_API_KEY',
    'MANAGER_CHAT_ID',
    'GPT_MODEL',
    'GPT_MAX_TOKENS',
    'GPT_TEMPERATURE',
    'SYSTEM_PROMPT',
    'get_main_keyboard',
    'get_admin_keyboard',
    'is_admin',
    'ADMIN_QUEUE',
    'TOKEN',
    'OPENAI_KEY',
    'MANAGER_ID'
    'process_admin_queue',
]
