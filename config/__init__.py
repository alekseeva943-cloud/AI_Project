# config/__init__.py

from .config import (
    TELEGRAM_TOKEN,
    OPENAI_API_KEY,
    MANAGER_CHAT_ID,
    SUPERADMIN_ID,
    CONTEXT_MESSAGE_COUNT,
    ADMIN_QUEUE,
    get_main_keyboard,
    get_admin_keyboard,
    get_settings_keyboard,
    get_admins_management_keyboard,
    get_empty_keyboard,
    is_admin
)

# Для обратной совместимости (если где-то используется)
from .config import (
    TELEGRAM_TOKEN as TOKEN,
    OPENAI_API_KEY as OPENAI_KEY,
    MANAGER_CHAT_ID as MANAGER_ID,
)

__all__ = [
    'TELEGRAM_TOKEN',
    'OPENAI_API_KEY',
    'MANAGER_CHAT_ID',
    'SUPERADMIN_ID',
    'CONTEXT_MESSAGE_COUNT',
    'ADMIN_QUEUE',
    'get_main_keyboard',
    'get_admin_keyboard',
    'get_settings_keyboard',
    'get_admins_management_keyboard',
    'get_empty_keyboard',
    'is_admin',
    'TOKEN',
    'OPENAI_KEY',
    'MANAGER_ID'
]
