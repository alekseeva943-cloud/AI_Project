# admin.py

import asyncio
import re
from typing import List
from config.config import get_settings_keyboard
from database import add_message, get_all_active_user_ids, get_users_with_phone, mark_user_blocked
from telegram import KeyboardButton, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import telegram
from telegram.ext import ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from config import get_admin_keyboard, is_admin as is_admin_user
import logging
from database import get_last_n_messages, get_total_users, get_client_info, search_clients, get_top_requests, get_total_clients_count, get_paginated_messages, get_total_messages_count, get_clients_paginated
from handlers.utilities import go_back
from handlers.admin_management import add_admin_start, handle_admin_input, remove_admin_start, show_admins_menu

logger = logging.getLogger(__name__)

# Состояния
AWAITING_SEARCH_QUERY = 1
AWAITING_BROADCAST_TYPE = 10
AWAITING_BROADCAST_TEXT = 11
AWAITING_BROADCAST_CONFIRM = 12
AWAITING_MESSAGE_TO_CLIENT = 20
PAGE_SIZE = 20


async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    is_admin = is_admin_user(user.id)
    if is_admin and not context.user_data.get('admin_panel_shown'):
        await update.message.reply_text("🛠 Добро пожаловать в админ-панель", reply_markup=get_admin_keyboard())
        context.user_data['admin_panel_shown'] = True
    return is_admin


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подменю 'Настройки'"""
    context.user_data['previous_state'] = 'settings_menu'
    await update.message.reply_text("⚙️ Настройки:", reply_markup=get_settings_keyboard())


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает админ-панель и запоминает предыдущее состояние"""
    if context.user_data.get('previous_state') != 'admin_panel':
        # Сохраняем состояние, откуда пришли (например, 'main_menu')
        context.user_data['return_to_after_admin'] = context.user_data.get(
            'previous_state', 'main_menu')
    context.user_data['previous_state'] = 'admin_panel'
    await update.message.reply_text("🛠 Админ-панель:", reply_markup=get_admin_keyboard())


async def handle_top_requests_period(update: Update, context: ContextTypes.DEFAULT_TYPE, period_text: str):
    period_map = {"7 дней": 7, "30 дней": 30, "Полгода": 180, "Год": 365}
    days = period_map.get(period_text, 7)
    top_requests = get_top_requests(days=days)

    if not top_requests:
        await update.message.reply_text(f"📭 Нет данных за {period_text}.", reply_markup=get_admin_keyboard())
        return

    total = sum(count for _, count in top_requests)
    report = f"📊 Топ запросов за {period_text}:\n\n"
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣",
              "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (topic, count) in enumerate(top_requests):
        emoji = emojis[i] if i < len(emojis) else "•"
        percent = round(count / total * 100, 1) if total else 0
        report += f"{emoji} {topic}: {count} ({percent}%)\n"
    report += f"\nВсего обращений: {total}"

    await update.message.reply_text(report, reply_markup=get_admin_keyboard())


async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return

    text = update.message.text
    if text == "📊 Статистика":
        await show_stats(update, context)
    elif text == "📈 Топ запросов":
        await show_top_requests_menu(update, context)
    elif text == "⚙️ Настройки":
        await update.message.reply_text("🛠 В разработке: Настройки")
    elif text == "👥 Пользователи":
        await show_users_page(update, context, page=0)
    elif text == "⬅️ Вернуться":
        await go_back(update, context)
    elif text == "⬅️ Назад":
        await update.message.reply_text("Возврат в админ-панель", reply_markup=get_admin_keyboard())
    elif text in ["7 дней", "30 дней", "Полгода", "Год"]:
        await handle_top_requests_period(update, context, text)
    else:
        await update.message.reply_text("❓ Неизвестная команда")


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from database import get_detailed_stats
        stats = get_detailed_stats()
        if not stats:
            await update.message.reply_text("❌ Не удалось загрузить статистику")
            return
        report = (
            "📊 <b>Расширенная статистика</b>\n\n"
            f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
            f"📱 <b>С телефоном:</b> {stats['with_phone']} ({stats['phone_conversion']}%)\n"
            f"🚫 <b>Заблокировали бота:</b> {stats['blocked_count']}\n"
            f"💬 <b>Активные чаты (24ч):</b> {stats['active_chats_24h']}\n\n"
            f"🆕 <b>Новых за сегодня:</b> {stats['new_today']}\n"
            f"🗓 <b>Новых за неделю:</b> {stats['new_last_7_days']}\n"
            f"📅 <b>Активных за 30 дней:</b> {stats['active_last_30_days']}"
        )
        await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке данных")


async def start_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Неверный ID клиента.")
        return ConversationHandler.END

    context.user_data['writing_to'] = user_id
    client_info = get_client_info(user_id)
    if not client_info:
        await query.message.reply_text("❌ Клиент не найден.")
        return ConversationHandler.END

    name = (client_info['first_name'] or '') + \
        (' ' + (client_info['last_name'] or ''))
    name = name.strip() or "Клиент"
    username = client_info.get('username')
    target = f'<a href="tg://resolve?domain={username}">@{username}</a>' if username else f"ID: <code>{user_id}</code>"

    await query.message.reply_text(
        f"✏️ Введите сообщение для {target}:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [["❌ Отмена"]], resize_keyboard=True, one_time_keyboard=True)
    )
    return AWAITING_MESSAGE_TO_CLIENT


async def send_message_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "❌ Отмена":
        context.user_data.pop('writing_to', None)
        await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    user_id = context.user_data.get('writing_to')
    if not user_id:
        await update.message.reply_text("❌ Ошибка: не указан получатель.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Пустое сообщение.")
        return AWAITING_MESSAGE_TO_CLIENT

    try:
        await context.bot.send_message(chat_id=user_id, text=text)
        add_message(user_id=user_id, role='assistant', content=text)
    except Exception as e:
        logger.error(f"Не удалось отправить {user_id}: {e}")
        if any(err in str(e) for err in ["bot was blocked", "user is deactivated", "chat not found"]):
            mark_user_blocked(user_id)
        await update.message.reply_text("❌ Не удалось отправить. Возможно, клиент заблокировал бота.", reply_markup=get_admin_keyboard())
        context.user_data.pop('writing_to', None)
        return ConversationHandler.END

    client_info = get_client_info(user_id)
    name = (client_info['first_name'] or '') + (' ' +
                                                (client_info['last_name'] or '')) if client_info else ""
    name = name.strip() or "Клиент"
    username = client_info.get('username') if client_info else None
    target = f'<a href="tg://resolve?domain={username}">@{username}</a>' if username else f"ID: <code>{user_id}</code>"

    context.user_data.pop('writing_to', None)
    await update.message.reply_text(f"✅ Сообщение отправлено {target}!", parse_mode="HTML", reply_markup=get_admin_keyboard())
    return ConversationHandler.END


async def cancel_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('writing_to', None)
    await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
    return ConversationHandler.END


def format_client(client: dict) -> tuple[str, InlineKeyboardMarkup]:
    name_parts = []
    if client['first_name']:
        name_parts.append(client['first_name'])
    if client['last_name']:
        name_parts.append(client['last_name'])
    name = ' '.join(name_parts) or "Без имени"
    username = f"@{client['username']}" if client['username'] else "—"
    phone = client['phone'] or "—"
    date_str = client['joined_at'][:10] if client['joined_at'] else "—"
    if date_str != "—":
        try:
            d = date_str.split('-')
            date_str = f"{d[2]}.{d[1]}.{d[0]}"
        except:
            pass

    text = (
        f"👤 Имя: {name}\n"
        f"🆔 ID: {client['user_id']}\n"
        f"🔗 Ссылка: tg://user?id={client['user_id']}\n"
        f"📱 Телефон: {phone}\n"
        f"@username: {username}\n"
        f"📅 Первое обращение: {date_str}\n"
        f"──────────────────────"
    )

    buttons = [
        InlineKeyboardButton(
            "💬 История", callback_data=f"chat_{client['user_id']}"),
        InlineKeyboardButton(
            "📨 Написать", callback_data=f"write_{client['user_id']}")
    ]
    if client['phone']:
        buttons.append(InlineKeyboardButton(
            "📞 Звонок", callback_data=f"call_{client['user_id']}"))

    return text, InlineKeyboardMarkup([buttons])


async def start_client_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Введите запрос для поиска:\n"
        "• Телефон (от 4 цифр)\n• Username (от 3 символов)\n• Имя/фамилия (от 5 букв)\n\n"
        "Нажмите «⬅️ Отмена», чтобы выйти.",
        reply_markup=ReplyKeyboardMarkup([["⬅️ Отмена"]], resize_keyboard=True)
    )
    return AWAITING_SEARCH_QUERY


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "⬅️ Отмена":
        await update.message.reply_text("Поиск отменён.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    clients = search_clients(text)
    if not clients:
        await update.message.reply_text(f"❌ Ничего не найдено по запросу:\n«{text}»", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    for client in clients[:10]:
        client_text, inline_keyboard = format_client(client)
        await update.message.reply_text(client_text, reply_markup=inline_keyboard)

    summary = f"✅ Найдено {len(clients)} клиент(а/ов)." if len(clients) <= 10 else \
              f"✅ Найдено {len(clients)} клиентов (показаны первые 10)."
    await update.message.reply_text(summary, reply_markup=get_admin_keyboard())
    return ConversationHandler.END


async def show_chat_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[1])
    messages = get_last_n_messages(user_id, n=20)

    if not messages:
        await query.edit_message_text("📭 Нет сообщений.")
        return

    history = f"💬 Переписка с клиентом {user_id}:\n\n"
    for msg in messages:
        role = "👤 Клиент" if msg['role'] == 'user' else "🤖 Бот"
        content = (msg['content'][:200] +
                   '...') if len(msg['content']) > 200 else msg['content']
        history += f"{role} ({msg['timestamp'][:16]}):\n{content}\n\n"

    await query.message.reply_text(history, reply_markup=get_admin_keyboard())


BROADCAST_TYPES = {"Всем клиентам": "all", "Только с телефоном": "with_phone"}


def format_phone_for_display(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return phone


async def handle_call_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "noop":
        return

    try:
        user_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Неверный ID.")
        return

    client_info = get_client_info(user_id)
    if not client_info or not client_info.get('phone'):
        await query.message.reply_text("❌ У клиента нет телефона.")
        return

    phone = client_info['phone']
    raw_phone = re.sub(r'\D', '', phone)
    if raw_phone.startswith('8'):
        raw_phone = '7' + raw_phone[1:]
    if not raw_phone.startswith('7'):
        raw_phone = '7' + raw_phone

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="📞 <b>Здравствуйте!</b>\nМенеджер хочет перезвонить.\nОжидайте звонок!",
            parse_mode="HTML"
        )
        notified = True
    except:
        notified = False

    display_phone = format_phone_for_display(phone)
    username = client_info.get('username')
    name = f"{client_info['first_name'] or ''} {client_info['last_name'] or ''}".strip(
    ) or "Без имени"
    parts = [f"📞 <b>Перезвонить клиенту</b>:\n• Имя: {name}"]
    if username:
        parts.append(
            f'• <a href="tg://resolve?domain={username}">:@{username}</a>')
    else:
        parts.append("• @username: —")
    parts.append(f'• Телефон: <a href="tel:+{raw_phone}">{display_phone}</a>')
    parts.append(f"• ID: <code>{user_id}</code>")
    parts.append(f"{'✅ Клиент уведомлён' if notified else '⚠️ Не уведомлён'}")

    await query.message.reply_text("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Всем клиентам", "Только с телефоном"], ["❌ Отмена"]]
    await update.message.reply_text("📤 Выберите тип рассылки:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAITING_BROADCAST_TYPE


async def handle_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("Рассылка отменена.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END
    if text not in BROADCAST_TYPES:
        await update.message.reply_text("Неверный тип.")
        return AWAITING_BROADCAST_TYPE

    context.user_data['broadcast_type'] = BROADCAST_TYPES[text]
    await update.message.reply_text("✏️ Введите текст рассылки:", reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True))
    return AWAITING_BROADCAST_TEXT


async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("Рассылка отменена.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END
    if len(text) > 4096:
        await update.message.reply_text("Текст слишком длинный.")
        return AWAITING_BROADCAST_TEXT

    context.user_data['broadcast_text'] = text
    broadcast_type = context.user_data['broadcast_type']
    recipients = get_all_active_user_ids(
    ) if broadcast_type == "all" else get_users_with_phone()
    context.user_data['recipient_count'] = len(recipients)

    await update.message.reply_text(
        f"📤 Подтверждение:\nТип: {text}\nПолучателей: {len(recipients)}\n✅ Отправить | ❌ Отмена",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Отправить", "❌ Отмена"]], resize_keyboard=True)
    )
    return AWAITING_BROADCAST_CONFIRM


async def perform_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение рассылки"""
    if update.message.text.strip() != "✅ Отправить":
        await update.message.reply_text("Рассылка отменена.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    text = context.user_data['broadcast_text']
    broadcast_type = context.user_data['broadcast_type']

    # Получаем список получателей
    if broadcast_type == "all":
        recipients = get_all_active_user_ids()
    else:
        recipients = get_users_with_phone()

    if not recipients:
        await update.message.reply_text("Нет получателей для рассылки.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    await update.message.reply_text(
        f"🚀 Начинаю рассылку ({len(recipients)} получателей)...\n"
        "Это может занять несколько секунд.",
        reply_markup=get_admin_keyboard()
    )

    # Счётчики
    success = 0
    blocked = 0
    errors = 0
    skipped = 0

    start_time = asyncio.get_event_loop().time()

    # Отправляем по одному с задержкой
    for user_id in recipients:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            success += 1
        except Exception as e:
            error_msg = str(e)
            if "Forbidden: bot was blocked by the user" in error_msg:
                blocked += 1
                mark_user_blocked(user_id)
            elif "Forbidden: user is deactivated" in error_msg:
                blocked += 1
                mark_user_blocked(user_id)
            elif "chat not found" in error_msg:
                skipped += 1
                mark_user_blocked(user_id)
            else:
                errors += 1
                logger.error(f"Ошибка рассылки для {user_id}: {e}")

        await asyncio.sleep(0.04)

    end_time = asyncio.get_event_loop().time()
    duration = round(end_time - start_time, 1)

    # Формируем отчёт
    report = (
        f"📤 Рассылка завершена!\n\n"
        f"Тип: {'Всем клиентам' if broadcast_type == 'all' else 'Только с телефоном'}\n"
        f"Текст: «{text[:200]}{'...' if len(text) > 200 else ''}»\n\n"
        f"📈 Статистика:\n"
        f"• Всего получателей: {len(recipients)}\n"
        f"• Успешно отправлено: {success}\n"
        f"• Заблокировали бота: {blocked}\n"
        f"• Ошибок отправки: {errors}\n"
        f"• Пропущено: {skipped}\n\n"
        f"⏱ Затрачено времени: {duration} сек"
    )

    if errors == 0 and blocked == 0:
        report += "\n\n✅ Рассылка завершена без сбоев."
    elif blocked > 0:
        report += f"\n\n⚠️ {blocked} пользователей заблокировали бота — их можно удалить из базы."
    else:
        report += "\n\n❗ Возникли ошибки при отправке."

    await update.message.reply_text(report)
    return ConversationHandler.END


async def show_top_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["7 дней", "30 дней"], ["Полгода", "Год"], ["⬅️ Назад"]]
    await update.message.reply_text("📊 Выберите период:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


async def show_users_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показывает страницу с пользователями (новые сверху) — по одному сообщению на клиента."""
    offset = page * PAGE_SIZE
    clients = get_clients_paginated(offset=offset, limit=PAGE_SIZE)
    total = get_total_clients_count()

    if not clients:
        text = "📭 Нет зарегистрированных пользователей."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 В админку", callback_data="users_back")]])
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)
        return

    # Отправляем каждого клиента отдельным сообщением
    for client in clients:
        client_text, inline_keyboard = format_client(client)
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            client_text, reply_markup=inline_keyboard
        )

    # === Навигация в последнем сообщении ===
        # === Навигация: только "Назад" и "Далее" ===
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"users_page_{page - 1}"))
    if len(clients) == PAGE_SIZE and (page + 1) * PAGE_SIZE < total:
        nav_buttons.append(InlineKeyboardButton(
            "Далее ➡️", callback_data=f"users_page_{page + 1}"))

    if nav_buttons:
        nav_keyboard = InlineKeyboardMarkup([nav_buttons])
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        summary_text = f"👥 Страница {page + 1} из {total_pages}"
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            summary_text, reply_markup=nav_keyboard
        )
    # Если нет кнопок — ничего не отправляем (как в поиске)
    else:
        # Нет навигации — просто кнопка возврата
        back_keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 В админку", callback_data="users_back")]])
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            "✅ Конец списка.",
            reply_markup=back_keyboard
        )


async def handle_users_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("users_page_"):
        try:
            page = int(data.split("_")[2])
            await show_users_page(update, context, page=page)
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Ошибка навигации.")
    else:
        # Убираем обработку "users_back"
        await query.message.reply_text("Неизвестное действие.")


# --- Обновлённый обработчик истории с пагинацией ---
async def show_chat_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        user_id = int(query.data.split("_")[1])
    except (IndexError, ValueError):
        await query.message.reply_text("❌ Неверный ID клиента.")
        return

    # Сохраняем user_id в user_data для пагинации
    context.user_data['viewing_chat_of'] = user_id
    await show_chat_page(update, context, page=0)


async def show_chat_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    query = update.callback_query
    user_id = context.user_data.get('viewing_chat_of')
    if not user_id:
        await query.message.reply_text("❌ Ошибка: не указан клиент.")
        return

    offset = page * PAGE_SIZE
    messages = get_paginated_messages(user_id, offset=offset, limit=PAGE_SIZE)
    total_msgs = get_total_messages_count(user_id)

    if not messages:
        text = "📭 Нет сообщений."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_users")]])
        await query.edit_message_text(text, reply_markup=keyboard)
        return

    # Формируем историю
    # Получаем имя клиента
    client_info = get_client_info(user_id)
    if client_info:
        name_parts = []
        if client_info.get('first_name'):
            name_parts.append(client_info['first_name'])
        if client_info.get('last_name'):
            name_parts.append(client_info['last_name'])
        display_name = ' '.join(name_parts) or f"ID {user_id}"
        username = f" (@{client_info['username']})" if client_info.get(
            'username') else ""
    else:
        display_name = f"ID {user_id}"
        username = ""

    history = f"💬 Переписка с {display_name}{username} (стр. {page + 1}):\n\n"
    for msg in messages:
        role = "👤 Клиент" if msg['role'] == 'user' else "🤖 Бот"
        content = (msg['content'][:200] +
                   '...') if len(msg['content']) > 200 else msg['content']
        # timestamp: "2025-05-01 12:34:56" → обрезаем до "2025-05-01 12:34"
        ts = msg['timestamp'][:16] if msg['timestamp'] else "—"
        history += f"{role} ({ts}):\n{content}\n\n"

    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Назад", callback_data=f"chat_page_{page - 1}"))
    if len(messages) == PAGE_SIZE and (page + 1) * PAGE_SIZE < total_msgs:
        nav_buttons.append(InlineKeyboardButton(
            "Далее ➡️", callback_data=f"chat_page_{page + 1}"))

    nav_buttons.append(InlineKeyboardButton(
        "🏠 К списку", callback_data="back_to_users"))
    keyboard = InlineKeyboardMarkup([nav_buttons])

    await query.edit_message_text(history, reply_markup=keyboard)


async def handle_chat_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_users":
        # или запоминать последнюю страницу — упрощаем
        await show_users_page(update, context, page=0)
        return

    if data.startswith("chat_page_"):
        try:
            page = int(data.split("_")[2])
            await show_chat_page(update, context, page=page)
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Ошибка загрузки истории.")
    else:
        await query.message.reply_text("Неизвестное действие.")


def get_admin_handlers():
    search_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(
            "🔍 Поиск клиентов"), start_client_search)],
        states={
            AWAITING_SEARCH_QUERY: [
                MessageHandler(filters.Text("⬅️ Отмена"),
                               lambda u, c: ConversationHandler.END),
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               handle_search_query),
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )

    broadcast_conversation = ConversationHandler(
        entry_points=[MessageHandler(
            filters.Text("📢 Рассылка"), start_broadcast)],
        states={
            AWAITING_BROADCAST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_type)],
            AWAITING_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_text)],
            AWAITING_BROADCAST_CONFIRM: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, perform_broadcast)]
        },
        fallbacks=[],
        allow_reentry=True
    )

    write_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            start_write_to_client, pattern=r"^write_\d+$")],
        states={
            AWAITING_MESSAGE_TO_CLIENT: [
                MessageHandler(filters.Text("❌ Отмена"),
                               cancel_write_to_client),
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               send_message_to_client)
            ]
        },
        fallbacks=[
            MessageHandler(filters.COMMAND, cancel_write_to_client),
            MessageHandler(filters.ALL, cancel_write_to_client)
        ],
        allow_reentry=True
    )

    # Управление админами — тоже через ConversationHandler
    admin_add_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(
            "➕ Добавить админа"), add_admin_start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input)]
        },
        fallbacks=[MessageHandler(
            filters.ALL, lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )

    admin_remove_conversation = ConversationHandler(
        entry_points=[MessageHandler(filters.Text(
            "🗑 Удалить админа"), remove_admin_start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input)]
        },
        fallbacks=[MessageHandler(
            filters.ALL, lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )

    # Основной обработчик для кнопок админ-панели
    admin_actions_handler = MessageHandler(
        filters.Text([
            "📊 Статистика", "📈 Топ запросов", "👥 Пользователи",
            "⬅️ Вернуться", "7 дней", "30 дней", "Полгода", "Год", "⬅️ Назад"
        ]),
        handle_admin_actions
    )

    # Обработчики колбэков
    callback_handlers = [
        CallbackQueryHandler(show_chat_history, pattern=r"^chat_\d+$"),
        CallbackQueryHandler(handle_call_request, pattern=r"^call_\d+$"),
        CallbackQueryHandler(handle_chat_navigation,
                             pattern=r"^chat_page_\d+$"),
        CallbackQueryHandler(handle_chat_navigation,
                             pattern=r"^back_to_users$"),
        CallbackQueryHandler(handle_chat_navigation,
                             pattern=r"^(chat_page_|back_to_users)$"),
    ]

    return [
        search_conversation,
        broadcast_conversation,
        write_conversation,
        admin_add_conversation,
        admin_remove_conversation,
        admin_actions_handler,
        MessageHandler(filters.Text("⚙️ Настройки"), show_settings_menu),
        MessageHandler(filters.Text("👥 Админы"),
                       show_admins_menu),  # ← добавлено
        *callback_handlers,
    ]
