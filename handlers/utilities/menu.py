"""
handlers/utilities/menu.py

Работа с меню Telegram-бота.

Содержит функции навигации между
основными разделами бота.
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import get_main_keyboard, is_admin
from config.keyboards import (
    get_help_keyboard,
    get_services_keyboard,
)

from handlers.utilities.services import (
    handle_services,
    show_auto_help_submenu,
)

from handlers.utilities.nav_stack import (
    push_state,
    clear_stack,
)


# ==========================================================
# Главное меню.
# ==========================================================

async def show_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает главное меню и очищает контекст навигации.
    """
    user = update.effective_user

    # Очищаем временный контекст
    context.user_data.pop("system_prompt", None)
    context.user_data.pop("help_topic", None)
    
    # Очищаем стек навигации при выходе в главное меню
    clear_stack(context)
    context.user_data.pop("admin_panel_shown", None)

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_keyboard(is_admin_user=is_admin(user.id)),
    )


# ==========================================================
# Меню помощи.
# ==========================================================

async def show_help_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает меню помощи.
    """
    push_state(context, "main_menu")

    await update.message.reply_text(
        "Здравствуйте! Что случилось?",
        reply_markup=get_help_keyboard(),
    )


# ==========================================================
# Навигация (оставлено для совместимости с обычным меню)
# ==========================================================

async def go_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Возвращает пользователя в предыдущее меню.
    Используется для обычного (не админского) меню.
    """
    from handlers.utilities.navigation import pop_state
    
    state = pop_state(context)

    if state == "help_menu":
        await show_help_menu(update, context)
    elif state == "services_menu":
        await handle_services(update, context)
    elif state == "auto_help_submenu":
        await show_auto_help_submenu(update, context)
    else:
        await show_main_menu(update, context)


async def cancel_current_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Отменяет текущий сценарий и возвращает в меню.
    """
    target = context.user_data.get("cancel_target")

    if target:
        await target(update, context)
    else:
        await go_back(update, context)

    return ConversationHandler.END