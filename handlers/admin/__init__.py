"""
handlers/admin/__init__.py

Публичный интерфейс пакета handlers.admin.

Позволяет импортировать основные функции модулей админ-панели
напрямую через пакет, без указания конкретного подмодуля.

Пример использования в main.py:
    from handlers.admin import get_admin_handlers, show_admin_panel
"""

# ==========================================================
# СПИСОК ПУБЛИЧНОГО API ПАКЕТА
# Сообщает анализаторам кода (например, Pylance), что эти 
# импорты не являются "лишними", а специально выносятся наружу.
# ==========================================================
__all__ = [
    # Роутинг
    "get_admin_handlers",
    
    # База знаний
    "handle_change_site",
    "handle_change_crawl_limit",
    "handle_build_new_base",
    "confirm_build_new_base",
    "handle_check_changes",
    "start_build_new_base",
    "handle_activate_new_base",
    "handle_knowledge_status",
    "handle_backup_restore",
    "save_rag_source_url",
    "save_crawl_limit",
    
    # Рассылка
    "start_broadcast",
    "handle_broadcast_type",
    "handle_broadcast_text",
    "perform_broadcast",
    
    # Меню и навигация
    "check_admin",
    "show_admin_panel",
    "show_settings_menu",
    "show_knowledge_base_menu",
    
    # Статистика
    "handle_top_requests_period",
    "handle_stats_period",
    "show_stats",
    
    # Пользователи
    "format_client",
    "start_client_search",
    "cancel_search",
    "handle_search_query",
    "show_users_page",
    "handle_users_navigation",
    "show_chat_history",
    "show_chat_page",
    "handle_chat_navigation",
    
    # Переписка
    "start_write_to_client",
    "send_message_to_client",
    "cancel_write_to_client",
]

# ==========================================================
# ИМПОРТЫ
# ==========================================================

# Регистрация обработчиков (сборка роутинга для Application)
from .handlers import get_admin_handlers

# Управление базой знаний (RAG)
from .knowledge_base import (
    handle_change_site,
    handle_change_crawl_limit,
    handle_build_new_base,
    confirm_build_new_base,
    handle_check_changes,
    start_build_new_base,
    handle_activate_new_base,
    handle_knowledge_status,
    handle_backup_restore,
    save_rag_source_url,
    save_crawl_limit,
)

# Массовая рассылка сообщений пользователям
from .broadcast import (
    start_broadcast,
    handle_broadcast_type,
    handle_broadcast_text,
    perform_broadcast,
)

# Главное меню и навигация админ-панели
from .panel import (
    check_admin,
    show_admin_panel,
    show_settings_menu,
    show_knowledge_base_menu,
)

# Статистика проекта и топ популярных запросов
from .stats import (
    handle_top_requests_period,
    handle_stats_period,
    show_stats,
)

# Пользователи: список, поиск, карточка, переписка
from .users import (
    format_client,
    start_client_search,
    cancel_search,
    handle_search_query,
    show_users_page,
    handle_users_navigation,
    show_chat_history,
    show_chat_page,
    handle_chat_navigation,
)

# Прямая переписка с клиентом из админки
from .client_messages import (
    start_write_to_client,
    send_message_to_client,
    cancel_write_to_client,
)