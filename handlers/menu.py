# handlers/menu.py

from telegram import Update
from telegram.ext import ContextTypes
from config.config import get_admin_keyboard, get_main_keyboard, is_admin


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает главное меню с учётом прав пользователя"""
    user = update.effective_user

    # --- СБРАСЫВАЕМ КОНТЕКСТ ---
    if 'system_prompt' in context.user_data:
        del context.user_data['system_prompt']
    if 'help_topic' in context.user_data:
        del context.user_data['help_topic']

    if is_admin(user.id):
        reply_markup = get_main_keyboard(is_admin_user=True)
    else:
        reply_markup = get_main_keyboard()

    await update.message.reply_text("Выберите услугу:", reply_markup=reply_markup)
