# handlers/admin_management.py

from telegram import Update
from telegram.ext import ContextTypes
from config.admin_keyboards import get_admins_management_keyboard
from config.config import SUPERADMIN_ID
from config.keyboards import get_cancel_keyboard
from database_old import get_all_admins, add_admin, remove_admin, DB_PATH
import logging

logger = logging.getLogger(__name__)


async def show_admins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != SUPERADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    admins = get_all_admins(DB_PATH)
    if not admins:
        text = "📭 Список админов пуст."
    else:
        lines = []
        for a in admins:
            name = f"{a['first_name'] or ''} {a['last_name'] or ''}".strip() or "—"
            username = f"@{a['username']}" if a['username'] else "—"
            marker = "👑" if a['user_id'] == SUPERADMIN_ID else "👤"
            lines.append(
                f"{marker} {name}\n   ID: {a['user_id']} | {username}")
        text = "👥 Список админов:\n\n" + "\n\n".join(lines)

    await update.message.reply_text(
        text,
        reply_markup=get_admins_management_keyboard()
    )
    context.user_data['previous_state'] = 'settings_menu'

async def add_admin_start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != SUPERADMIN_ID:
        return

    # Куда возвращаться при нажатии "❌ Отмена"
    context.user_data["cancel_target"] = show_admins_menu

    await update.message.reply_text(
        "Введите ID или username (например: 123456789 или @Al_leks):",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data["awaiting_action"] = "add_admin"

    return 1


async def remove_admin_start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != SUPERADMIN_ID:
        return

    admins = get_all_admins(DB_PATH)
    non_super = [
        admin
        for admin in admins
        if admin["user_id"] != SUPERADMIN_ID
    ]

    if not non_super:
        await update.message.reply_text(
            "📭 Нет админов для удаления."
        )
        return

    # Куда возвращаться при нажатии "❌ Отмена"
    context.user_data["cancel_target"] = show_admins_menu

    ids = "\n".join(
        str(admin["user_id"])
        for admin in non_super
    )

    await update.message.reply_text(
        f"Введите ID администратора для удаления:\n\n"
        f"Доступные ID:\n{ids}",
        reply_markup=get_cancel_keyboard()
    )

    context.user_data["awaiting_action"] = "remove_admin"

    return 1

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != SUPERADMIN_ID:
        return

    action = context.user_data.get('awaiting_action')
    if not action:
        return

    text = update.message.text.strip()
    context.user_data['awaiting_action'] = None

    try:
        if action == 'add_admin':
            # Определяем тип: ID или username
            if text.isdigit():
                admin_id = int(text)
                # Получаем данные из Telegram
                try:
                    chat = await context.bot.get_chat(admin_id)
                    username = chat.username
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    username = first_name = last_name = None
            elif text.startswith('@'):
                username = text[1:]
                # Получаем ID по username
                try:
                    chat = await context.bot.get_chat(text)
                    admin_id = chat.id
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    await update.message.reply_text("❌ Не удалось найти пользователя по username.")
                    return
            else:
                # Предполагаем, что это username без @
                username = text
                try:
                    chat = await context.bot.get_chat(f"@{text}")
                    admin_id = chat.id
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    await update.message.reply_text("❌ Не удалось найти пользователя по username.")
                    return

            if admin_id == SUPERADMIN_ID:
                await update.message.reply_text("👑 Этот пользователь — суперадмин.")
            else:
                add_admin(DB_PATH, admin_id, username, first_name,
                          last_name, added_by=SUPERADMIN_ID)
                await update.message.reply_text(f"✅ Админ добавлен:\nID: {admin_id}\nUsername: @{username or '—'}")

        elif action == 'remove_admin':
            if not text.isdigit():
                await update.message.reply_text("❌ Введите корректный ID (только цифры).")
                return
            admin_id = int(text)
            if admin_id == SUPERADMIN_ID:
                await update.message.reply_text("❌ Нельзя удалить суперадмина.")
            else:
                remove_admin(DB_PATH, admin_id)
                await update.message.reply_text(f"🗑 Админ с ID {admin_id} удалён.")

    except Exception as e:
        logger.error(f"Ошибка при управлении админом: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка при обработке. Проверьте данные и повторите.")
