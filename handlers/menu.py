# handlers/menu.py

"""
Работа с главным меню Telegram-бота.

Назначение:
- очистка временного контекста;
- отображение главного меню;
- выбор клавиатуры по роли пользователя.
"""

from telegram import Update
from telegram.ext import ContextTypes

from config.config import is_admin
from config.keyboards import get_main_keyboard


# ==========================================================
# Главное меню.
# ==========================================================

async def main_menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Очищает временный контекст
    и отображает главное меню.

    Returns:
        None.
    """

    user = update.effective_user

    # Удаляем временный контекст,
    # накопленный в процессе диалога.
    context.user_data.pop("system_prompt", None)
    context.user_data.pop("help_topic", None)

    reply_markup = (
        get_main_keyboard(is_admin_user=True)
        if is_admin(user.id)
        else get_main_keyboard()
    )

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=reply_markup,
    )