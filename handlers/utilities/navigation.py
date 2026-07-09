"""
handlers/utilities/navigation.py

Утилиты для навигации между меню.
Использует ленивые импорты (внутри функций) модулей админки,
чтобы избежать циклической зависимости при запуске бота.
"""

from telegram import Update
from telegram.ext import ContextTypes

# Импортируем только то, что не тянет за собой админку
from config.admin_keyboards import (
    get_settings_keyboard,
    get_knowledge_base_keyboard,
)
from handlers.utilities.menu import show_main_menu

# Импортируем чистую логику стека из нового файла
from handlers.utilities.nav_stack import pop_state


async def navigate_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Универсальный обработчик кнопки "Назад".
    Достаёт предыдущее состояние из стека и показывает нужное меню.
    """
    target_state = pop_state(context)
    
    if target_state is None:
        # Стек пуст — выходим в главное меню пользователя
        await show_main_menu(update, context)
        return
    
    # ==========================================
    # ЛЕНИВЫЕ ИМПОРТЫ АДМИНКИ
    # Они выполняются только в момент нажатия кнопки "Назад",
    # а не при старте бота. Это 100% убирает циклический импорт.
    # ==========================================
    
    if target_state == "admin_panel":
        from handlers.admin.panel import show_admin_panel
        await show_admin_panel(update, context)
        
    elif target_state == "settings_menu":
        await update.message.reply_text(
            "⚙️ Настройки:",
            reply_markup=get_settings_keyboard(),
        )
        
    elif target_state == "knowledge_base_menu":
        from config.buttons import BTN_KNOWLEDGE_BASE
        await update.message.reply_text(
            BTN_KNOWLEDGE_BASE,
            reply_markup=get_knowledge_base_keyboard(),
        )
        
    elif target_state == "admins_menu":
        from handlers.admin_management import show_admins_menu
        await show_admins_menu(update, context)
        
    elif target_state == "stats_period_menu":
        from handlers.admin.stats import show_stats_menu
        await show_stats_menu(update, context)
        
    elif target_state == "top_requests_period_menu":
        from handlers.admin.stats import show_top_requests_menu
        await show_top_requests_menu(update, context)
        
    elif target_state == "users_list":
        from handlers.admin.users import show_users_page
        await show_users_page(update, context, page=0)
        
    else:
        # На всякий случай, если состояние неизвестно
        await show_main_menu(update, context)