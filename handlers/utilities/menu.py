# handlers/utilities/menu.py

"""
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


# ==========================================================
# Главное меню.
# ==========================================================

async def show_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает главное меню
    и очищает временный контекст.

    Returns:
        None.
    """

    user = update.effective_user

    # Очищаем временный контекст,
    # используемый в текущем диалоге.
    context.user_data.pop("system_prompt", None)
    context.user_data.pop("help_topic", None)

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_keyboard(
            is_admin_user=is_admin(user.id)
        ),
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

    Returns:
        None.
    """

    context.user_data["previous_state"] = "main_menu"

    await update.message.reply_text(
        "Здравствуйте! Что случилось?",
        reply_markup=get_help_keyboard(),
    )


# ==========================================================
# Навигация.
# ==========================================================

async def go_back(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Возвращает пользователя
    в предыдущее меню.

    Returns:
        None.
    """

    from .services import (
        handle_services,
        show_auto_help_submenu,
    )

    state = context.user_data.get(
        "previous_state"
    )

    if state == "help_menu":
        await show_help_menu(update, context)

    elif state == "services_menu":
        await handle_services(update, context)

    elif state == "auto_help_submenu":
        await show_auto_help_submenu(
            update,
            context,
        )

    else:
        await show_main_menu(update, context)


async def cancel_current_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Отменяет текущий сценарий
    и возвращает пользователя
    в предыдущее меню.

    Returns:
        ConversationHandler.END.
    """

    target = context.user_data.get(
        "cancel_target"
    )

    if target:
        await target(update, context)

    return ConversationHandler.END