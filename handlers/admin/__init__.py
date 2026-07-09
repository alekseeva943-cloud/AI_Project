"""
Публичный интерфейс пакета handlers.admin.

Позволяет импортировать основные функции
через:

from handlers.admin import ...
"""
from .handlers import get_admin_handlers

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

from .broadcast import (
    start_broadcast,
    handle_broadcast_type,
    handle_broadcast_text,
    perform_broadcast,
)

from .panel import (
    check_admin,
    show_admin_panel,
    show_settings_menu,
    show_knowledge_base_menu,
)

from .stats import (
    handle_top_requests_period,
    handle_stats_period,
    show_stats,
)

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

from .client_messages import (
    start_write_to_client,
    send_message_to_client,
    cancel_write_to_client,
)