"""
handlers/admin/handlers.py

Регистрация всех обработчиков административной панели.

Назначение модуля:

- создание ConversationHandler для пошаговых сценариев;
- регистрация MessageHandler;
- регистрация CallbackQueryHandler;
- объединение всех обработчиков административной панели
  в единый список для подключения в main.py.
"""

import logging

from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import buttons as btn

from handlers.utilities import (
    cancel_current_action,
)

from handlers.admin.constants import (
    AWAITING_SEARCH_QUERY,
    AWAITING_MESSAGE_TO_CLIENT,
    AWAITING_BROADCAST_TYPE,
    AWAITING_BROADCAST_TEXT,
    AWAITING_BROADCAST_CONFIRM,
    AWAITING_RAG_SOURCE_URL,
    AWAITING_CRAWL_LIMIT,
    AWAITING_BUILD_CONFIRMATION,
    AWAITING_ACTIVATE_CONFIRMATION,
    AWAITING_RESTORE_CONFIRMATION,
)

from handlers.admin.users import (    
    start_client_search,
    handle_search_query,
    show_chat_history,
    handle_chat_navigation,
)

from handlers.admin.client_messages import (
    start_write_to_client,
    send_message_to_client,
    cancel_write_to_client,
)

from handlers.admin.broadcast import (
    start_broadcast,
    handle_broadcast_type,
    handle_broadcast_text,
    perform_broadcast,
)

from handlers.admin.panel import (
    handle_admin_actions,
    show_settings_menu,
    show_knowledge_base_menu,
)

from handlers.admin.knowledge_base import (
    handle_change_site,
    save_rag_source_url,
    handle_change_crawl_limit,
    save_crawl_limit,
    handle_build_new_base,
    confirm_build_new_base,
    handle_check_changes,
    handle_activate_new_base,
    confirm_activate_new_base,
    handle_backup_restore,
    confirm_backup_restore,
    handle_knowledge_status,
)

from handlers.admin_management import (
    show_admins_menu,
    add_admin_start,
    remove_admin_start,
    handle_admin_input,
)

logger = logging.getLogger(__name__)

def get_admin_handlers():

    # ======================================================
    # Поиск клиента
    # ======================================================
    search_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_CLIENT_SEARCH),
                start_client_search
            )
        ],
        states={
            AWAITING_SEARCH_QUERY: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_search_query
                ),
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )

    # ======================================================
    # Массовая рассылка
    # ======================================================
    broadcast_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_BROADCAST),
                start_broadcast
            )
        ],
        states={
            AWAITING_BROADCAST_TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_broadcast_type
                )
            ],
            AWAITING_BROADCAST_TEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_broadcast_text
                )
            ],
            AWAITING_BROADCAST_CONFIRM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    perform_broadcast
                )
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )

    # ======================================================
    # Написать клиенту
    # ======================================================
    write_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                start_write_to_client,
                pattern=r"^write_\d+$"
            )
        ],
        states={
            AWAITING_MESSAGE_TO_CLIENT: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    send_message_to_client
                )
            ]
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, cancel_write_to_client),
            MessageHandler(filters.ALL, cancel_write_to_client)
        ],
        allow_reentry=True
    )

    # ======================================================
    # Добавление администратора
    # ======================================================
    admin_add_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_ADD_ADMIN),
                add_admin_start
            )
        ],
        states={
            1: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_input
                )
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.ALL,
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Удаление администратора
    # ======================================================
    admin_remove_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_REMOVE_ADMIN),
                remove_admin_start
            )
        ],
        states={
            1: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),

                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    handle_admin_input
                )
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.ALL,
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Изменение сайта базы знаний
    # ======================================================
    change_site_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_CHANGE_SITE),
                handle_change_site
            )
        ],
        states={
            AWAITING_RAG_SOURCE_URL: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_rag_source_url
                ),
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Text(btn.BTN_CANCEL),
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Подтверждение запуска сборки базы знаний
    # ======================================================
    build_confirm_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_BUILD_NEW_BASE),
                handle_build_new_base
            )
        ],
        states={
            AWAITING_BUILD_CONFIRMATION: [

                MessageHandler(
                    filters.Text(btn.BTN_CONFIRM_BUILD),
                    confirm_build_new_base
                ),

                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                )
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Text(btn.BTN_CANCEL),
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Подтверждение активации новой базы знаний
    # ======================================================
    activate_confirm_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_ACTIVATE_NEW_BASE),
                handle_activate_new_base
            )
        ],
        states={
            AWAITING_ACTIVATE_CONFIRMATION: [
                MessageHandler(
                    filters.Text(btn.BTN_CONFIRM_BUILD),
                    confirm_activate_new_base
                ),
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                )
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Text(btn.BTN_CANCEL),
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Подтверждение отката на резервную копию
    # ======================================================
    restore_confirm_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_BACKUP),
                handle_backup_restore
            )
        ],
        states={
            AWAITING_RESTORE_CONFIRMATION: [
                MessageHandler(
                    filters.Text(btn.BTN_CONFIRM_BUILD),
                    confirm_backup_restore
                ),
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                )
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Text(btn.BTN_CANCEL),
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Изменение лимита страниц для парсера
    # ======================================================
    change_crawl_limit_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Text(btn.BTN_CRAWL_LIMIT),
                handle_change_crawl_limit
            )
        ],
        states={
            AWAITING_CRAWL_LIMIT: [
                MessageHandler(
                    filters.Text(btn.BTN_CANCEL),
                    cancel_current_action
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_crawl_limit
                ),
            ]
        },
        fallbacks=[
            MessageHandler(
                filters.Text(btn.BTN_CANCEL),
                cancel_current_action
            )
        ],
        allow_reentry=True
    )

    # ======================================================
    # Общий обработчик кнопок админ-панели
    # ======================================================
    admin_actions_handler = MessageHandler(
        filters.Text([

            # Основное меню
            btn.BTN_STATS,
            btn.BTN_TOP_REQUESTS,
            btn.BTN_USERS,

            # Периоды статистики
            btn.BTN_TODAY,
            btn.BTN_WEEK,
            btn.BTN_MONTH,
            btn.BTN_STATS_YEAR,

            # Периоды топ-запросов
            btn.BTN_PERIOD_7_DAYS,
            btn.BTN_PERIOD_30_DAYS,
            btn.BTN_PERIOD_HALF_YEAR,
            btn.BTN_PERIOD_YEAR,

            # Навигация
            btn.BTN_PREVIOUS,
            btn.BTN_BACK,
            btn.BTN_CANCEL,

        ]),
        handle_admin_actions
    )

    # ======================================================
    # Callback-кнопки
    # ======================================================
    callback_handlers = [
        CallbackQueryHandler(
            show_chat_history,
            pattern=r"^chat_\d+$"
        ),
        CallbackQueryHandler(
            handle_chat_navigation,
            pattern=r"^chat_page_\d+$"
        ),
        CallbackQueryHandler(
            handle_chat_navigation,
            pattern=r"^back_to_users$"
        ),
    ]

    # ======================================================
    # Возвращаем все обработчики
    # ======================================================
    return [

        # ConversationHandler
        search_conversation,
        broadcast_conversation,
        write_conversation,
        admin_add_conversation,
        admin_remove_conversation,
        change_site_conversation,
        change_crawl_limit_conversation,
        build_confirm_conversation,
        activate_confirm_conversation,
        restore_confirm_conversation,

        # Общие кнопки админки
        admin_actions_handler,

        MessageHandler(
            filters.Text(btn.BTN_SETTINGS),
            show_settings_menu
        ),

        MessageHandler(
            filters.Text(btn.BTN_ADMINS),
            show_admins_menu
        ),

        # ==================================================
        # Управление базой знаний
        # ==================================================

        MessageHandler(
            filters.Text(btn.BTN_KNOWLEDGE_BASE),
            show_knowledge_base_menu
        ),

        MessageHandler(
            filters.Text(btn.BTN_CHECK_CHANGES),
            handle_check_changes
        ),

        MessageHandler(
            filters.Text(btn.BTN_KNOWLEDGE_STATUS),
            handle_knowledge_status
        ),

        # CallbackQuery
        *callback_handlers,
    ]