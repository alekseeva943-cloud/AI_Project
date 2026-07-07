# admin.py
# Файл отвечает за работу административной панели бота.
# Здесь находятся:
# - статистика;
# - рассылки;
# - поиск клиентов;
# - просмотр переписок;
# - управление пользователями;
# - административные диалоги и служебные обработчики.

# admin.py

import os
import asyncio
import shutil
import re
from typing import List
from unittest import result
import json
from pathlib import Path
from config.keyboards import (
    get_cancel_keyboard,
    get_confirm_keyboard
)
from config.config import is_admin as is_admin_user

from config.admin_keyboards import (
    get_admin_keyboard,
    get_settings_keyboard,
    get_admins_management_keyboard,
    get_broadcast_type_keyboard,
    get_stats_keyboard,
    get_top_requests_keyboard,
    get_knowledge_base_keyboard,
    get_broadcast_confirm_keyboard
)
from database import (
    add_message,
    get_all_active_user_ids,
    get_users_with_phone,
    mark_user_blocked,
)
from telegram import KeyboardButton, Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import telegram
from telegram.ext import ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
import logging
from database import (
    get_client_info,
    get_clients_paginated,
    get_paginated_messages,
    get_top_requests,
    get_total_clients_count,
    get_total_messages_count,
    get_total_users,
    search_clients,
)
from handlers.utilities import go_back, cancel_current_action
from handlers.admin_management import add_admin_start, handle_admin_input, remove_admin_start, show_admins_menu

from config import buttons as btn

logger = logging.getLogger(__name__)

# ==========================================================
# СОСТОЯНИЯ ConversationHandler
#
# Каждый ConversationHandler использует уникальный числовой
# идентификатор состояния, в котором находится пользователь.
#
# Пример:
#
# Пользователь нажал:
# "🔍 Поиск клиента"
#
# Бот переходит в состояние:
# AWAITING_SEARCH_QUERY
#
# и начинает ожидать ввод поискового запроса.
# ==========================================================

# Ожидание поискового запроса администратора.
AWAITING_SEARCH_QUERY = 1

# Ожидание выбора типа рассылки.
AWAITING_BROADCAST_TYPE = 10

# Ожидание текста рассылки.
AWAITING_BROADCAST_TEXT = 11

# Ожидание подтверждения отправки рассылки.
AWAITING_BROADCAST_CONFIRM = 12

# Ожидание сообщения для конкретного клиента.
AWAITING_MESSAGE_TO_CLIENT = 20

# Ожидание нового адреса сайта для RAG-парсера.
AWAITING_RAG_SOURCE_URL = 30

# Состояние кол-ва страниц для парсера
AWAITING_CRAWL_LIMIT = 1002

# Ожидание подтверждения запуска сборки базы
AWAITING_BUILD_CONFIRMATION = 1003


# ==========================================================
# НАСТРОЙКИ ИНТЕРФЕЙСА
#
# Параметры отображения интерфейса и пагинации.
# ==========================================================

# Количество пользователей на одной странице списка.
PAGE_SIZE = 10


# Проверяет, является ли пользователь администратором и при необходимости показывает админ-панель.
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    is_admin = is_admin_user(user.id)
    if is_admin and not context.user_data.get('admin_panel_shown'):
        await update.message.reply_text("🛠 Добро пожаловать в админ-панель", reply_markup=get_admin_keyboard())
        context.user_data['admin_panel_shown'] = True
    return is_admin


# Показывает раздел настроек администратора.
async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подменю 'Настройки'"""
    context.user_data['previous_state'] = 'settings_menu'
    await update.message.reply_text("⚙️ Настройки:", reply_markup=get_settings_keyboard())


# Показывает меню управления базой знаний.
async def show_knowledge_base_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["previous_state"] = "knowledge_base_menu"

    await update.message.reply_text(
        btn.BTN_KNOWLEDGE_BASE,
        reply_markup=get_knowledge_base_keyboard()
    )

# Показывает главное меню административной панели.


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает админ-панель и запоминает предыдущее состояние"""
    if context.user_data.get('previous_state') != 'admin_panel':
        # Сохраняем состояние, откуда пришли (например, 'main_menu')
        context.user_data['return_to_after_admin'] = context.user_data.get(
            'previous_state', 'main_menu')
    context.user_data['previous_state'] = 'admin_panel'
    await update.message.reply_text("🛠 Админ-панель:", reply_markup=get_admin_keyboard())


# Формирует статистику популярных запросов за выбранный период.
async def handle_top_requests_period(update: Update, context: ContextTypes.DEFAULT_TYPE, period_text: str):
    period_map = {btn.BTN_PERIOD_7_DAYS: 7, btn.BTN_PERIOD_30_DAYS: 30,
                  btn.BTN_PERIOD_HALF_YEAR: 180, btn.BTN_PERIOD_YEAR: 365}
    days = period_map.get(period_text, 7)

    logger.info(
        f"[TOP REQUESTS] period={period_text}, days={days}"
    )
    top_requests = get_top_requests(days=days)

    logger.info(
        f"[TOP REQUESTS RESULT] {top_requests}"
    )

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


# Формирует статистику пользователей за выбранный период.
async def handle_stats_period(update: Update, context: ContextTypes.DEFAULT_TYPE, period_text: str):

    period_map = {
        btn.BTN_TODAY: 1,
        btn.BTN_WEEK: 7,
        btn.BTN_MONTH: 30,
        btn.BTN_STATS_YEAR: 365
    }

    days = period_map.get(period_text)

    from database import get_detailed_stats

    stats = get_detailed_stats(days=days)

    report = (
        f"📊 <b>Статистика за период: {period_text}</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {stats['total_users']}\n"
        f"📱 <b>С телефоном:</b> {stats['with_phone']} ({stats['phone_conversion']}%)\n"
        f"🚫 <b>Заблокировали бота:</b> {stats['blocked_count']}\n"
        f"💬 <b>Активные чаты:</b> {stats['active_chats_24h']}\n\n"
        f"🆕 <b>Новых пользователей:</b> {stats['new_today']}\n"
        f"📅 <b>Активных пользователей:</b> {stats['active_last_30_days']}"
    )

    await update.message.reply_text(
        report,
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )


# Обрабатывает нажатия кнопок административной панели.
async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return

    text = update.message.text

    if text == btn.BTN_STATS:
        await show_top_requests_menu(update, context)

    elif text == btn.BTN_TOP_REQUESTS:
        await show_stats_menu(update, context)

    elif text == btn.BTN_SETTINGS:
        logger.warning("СРАБОТАЛ HANDLE_ADMIN_ACTIONS SETTINGS")
        await update.message.reply_text("TEST SETTINGS")

    elif text == btn.BTN_USERS:
        await show_users_page(update, context, page=0)

    elif text in [btn.BTN_BACK, btn.BTN_PREVIOUS, btn.BTN_CANCEL]:
        await go_back(update, context)

    # Периоды статистики.
    elif text in [
        btn.BTN_TODAY,
        btn.BTN_WEEK,
        btn.BTN_MONTH,
        btn.BTN_STATS_YEAR
    ]:
        await handle_stats_period(update, context, text)

    # Периоды топ-запросов.
    elif text in [
        btn.BTN_PERIOD_7_DAYS,
        btn.BTN_PERIOD_30_DAYS,
        btn.BTN_PERIOD_HALF_YEAR,
        btn.BTN_PERIOD_YEAR
    ]:
        await handle_top_requests_period(update, context, text)

    else:
        await update.message.reply_text("❓ Неизвестная команда")


# Показывает расширенную статистику проекта.
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


# Запускает режим отправки сообщения конкретному клиенту.
async def start_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cancel_target"] = show_admin_panel
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
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_MESSAGE_TO_CLIENT


# Отправляет введённое администратором сообщение клиенту.
async def send_message_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == btn.BTN_CANCEL:
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


# Отменяет режим написания сообщения клиенту.
async def cancel_write_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('writing_to', None)
    await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
    return ConversationHandler.END


# Формирует карточку клиента для отображения в админке.
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


# Запускает поиск клиентов по имени, телефону или username.
async def start_client_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cancel_target"] = show_admin_panel
    await update.message.reply_text(
        "🔍 Введите запрос для поиска:\n"
        "• Телефон (от 4 цифр)\n• Username (от 3 символов)\n• Имя/фамилия (от 5 букв)\n\n"
        "Нажмите «⬅❌ Отмена», чтобы выйти.",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_SEARCH_QUERY


# Отменяет поиск клиентов.
async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Поиск отменён.",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


# Завершает административный диалог.
async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END

# Обрабатывает поисковый запрос администратора.


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == btn.BTN_CANCEL:
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


BROADCAST_TYPES = {btn.BTN_BROADCAST_ALL: "all",
                   btn.BTN_BROADCAST_PHONE: "with_phone"}


# Приводит телефон к удобному для отображения формату.
def format_phone_for_display(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return phone


# Показывает администратору данные для звонка клиенту.
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


# Запускает мастер создания рассылки.
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cancel_target"] = show_admin_panel
    await update.message.reply_text(
        "📤 Выберите тип рассылки:",
        reply_markup=get_broadcast_type_keyboard()
    )

    return AWAITING_BROADCAST_TYPE


# Обрабатывает выбор типа рассылки.
async def handle_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == btn.BTN_CANCEL:
        await update.message.reply_text("Рассылка отменена.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END
    if text not in BROADCAST_TYPES:
        await update.message.reply_text("Неверный тип.")
        return AWAITING_BROADCAST_TYPE

    context.user_data['broadcast_type'] = BROADCAST_TYPES[text]
    await update.message.reply_text("✏️ Введите текст рассылки:", reply_markup=get_cancel_keyboard())
    return AWAITING_BROADCAST_TEXT


# Сохраняет текст рассылки и готовит подтверждение отправки.
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == btn.BTN_CANCEL:
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
        reply_markup=get_broadcast_confirm_keyboard()
    )
    return AWAITING_BROADCAST_CONFIRM


# Выполняет массовую рассылку пользователям.
async def perform_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение рассылки"""
    if update.message.text.strip() != btn.BTN_SEND:
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


# Показывает меню выбора периода для топа запросов.
async def show_top_requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Выберите период для анализа популярных запросов:",
        reply_markup=get_top_requests_keyboard()
    )


# Показывает меню выбора периода статистики проекта.
async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 Выберите период статистики:",
        reply_markup=get_stats_keyboard()
    )


# Показывает страницу списка пользователей.
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
            btn.BTN_PREVIOUS, callback_data=f"users_page_{page - 1}"))
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


# Обрабатывает переключение страниц пользователей.
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
# Открывает историю переписки выбранного клиента.
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


# Показывает страницу истории переписки клиента.
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
            [[InlineKeyboardButton(btn.BTN_PREVIOUS, callback_data="back_to_users")]])
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
            btn.BTN_PREVIOUS, callback_data=f"chat_page_{page - 1}"))
    if len(messages) == PAGE_SIZE and (page + 1) * PAGE_SIZE < total_msgs:
        nav_buttons.append(InlineKeyboardButton(
            "Далее ➡️", callback_data=f"chat_page_{page + 1}"))

    nav_buttons.append(InlineKeyboardButton(
        "🏠 К списку", callback_data="back_to_users"))
    keyboard = InlineKeyboardMarkup([nav_buttons])

    await query.edit_message_text(history, reply_markup=keyboard)


# Обрабатывает навигацию по истории переписки.
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


# Запускает сценарий изменения сайта для базы знаний.
async def handle_change_site(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["cancel_target"] = show_knowledge_base_menu
    settings_path = (
        Path(__file__).resolve().parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )

    with open(
        settings_path,
        "r",
        encoding="utf-8"
    ) as f:
        settings = json.load(f)

    current_url = settings.get(
        "base_url",
        "Не настроен"
    )

    await update.message.reply_text(
        f"📚 {btn.BTN_KNOWLEDGE_BASE}\n\n"
        f"Текущий источник знаний:\n\n"
        f"{current_url}\n\n"
        f"Введите новый адрес сайта.\n\n"
        f"Для отмены нажмите кнопку:\n"
        f"{btn.BTN_CANCEL}",
        reply_markup=get_cancel_keyboard()
    )

    return AWAITING_RAG_SOURCE_URL


# ======================================================
# Запускает сценарий изменения лимита страниц.
#
# Позволяет указать:
# 10  -> парсить 10 страниц
# 100 -> парсить 100 страниц
# 0   -> парсить весь сайт без ограничений
# ======================================================
async def handle_change_crawl_limit(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    context.user_data["cancel_target"] = show_knowledge_base_menu

    settings_path = (
        Path(__file__).resolve().parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )

    with open(
        settings_path,
        "r",
        encoding="utf-8"
    ) as f:
        settings = json.load(f)

    current_limit = settings.get(
        "crawl_limit",
        4
    )

    display_limit = (
        "Все страницы"
        if current_limit == 0
        else str(current_limit)
    )

    await update.message.reply_text(
        f"📄 Текущий лимит страниц:\n\n"
        f"{display_limit}\n\n"
        f"Введите новый лимит.\n\n"
        f"0 = весь сайт\n"
        f"10 = первые 10 страниц\n"
        f"100 = первые 100 страниц\n\n"
        f"Для отмены нажмите:\n"
        f"{btn.BTN_CANCEL}",
        reply_markup=get_cancel_keyboard()
    )

    return AWAITING_CRAWL_LIMIT


# ======================================================
# Запрашивает подтверждение перед запуском сборки базы.
#
# Нужно чтобы случайное нажатие кнопки не запускало
# дорогой и долгий процесс парсинга.
# ======================================================
async def handle_build_new_base(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    # При отмене возвращаемся в меню базы знаний
    context.user_data["cancel_target"] = (
        show_knowledge_base_menu
    )

    settings_path = (
        Path(__file__).resolve().parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )

    with open(
        settings_path,
        "r",
        encoding="utf-8"
    ) as f:
        settings = json.load(f)

    current_site = settings.get(
        "base_url",
        "Не указан"
    )

    current_limit = settings.get(
        "crawl_limit",
        4
    )

    # Для пользователя отображаем понятное значение
    display_limit = (
        "Все страницы"
        if current_limit == 0
        else str(current_limit)
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [btn.BTN_CONFIRM_BUILD],
            [btn.BTN_CANCEL]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⚠️ Вы собираетесь начать сборку новой базы знаний.\n\n"

        f"🌐 Сайт:\n"
        f"{current_site}\n\n"

        f"📄 Лимит страниц:\n"
        f"{display_limit}\n\n"

        "Процесс может занять длительное время "
        "и использовать токены OpenAI.\n\n"

        "Продолжить?",
        reply_markup=keyboard
    )

    return AWAITING_BUILD_CONFIRMATION


# ======================================================
# Пользователь подтвердил запуск сборки базы.
# ======================================================
async def confirm_build_new_base(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    await start_build_new_base(
        update,
        context
    )

    return ConversationHandler.END


# ======================================================
# 🔍 Проверка изменений между версиями базы знаний
# ======================================================
async def handle_check_changes(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    import json
    from pathlib import Path

    def load_stats(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    # ======================
    # пути к базам
    # ======================
    active_stats_path = Path("data/build_stats.json")
    new_stats_path = Path("parser/output/build_stats.json")
    backup_stats_path = Path("backup/build_stats.json")

    active = load_stats(active_stats_path)
    new = load_stats(new_stats_path)
    backup = load_stats(backup_stats_path)

    # ======================
    # сравнение
    # ======================
    def format_block(name, stats):
        return (
            f"📦 {name}\n"
            f"📄 Страниц: {stats.get('pages', 0)}\n"
            f"🧱 Блоков: {stats.get('blocks', 0)}\n"
            f"📦 Чанков: {stats.get('chunks', 0)}\n"
            f"🧠 Токенов: {stats.get('tokens', 0)}\n"
            f"💰 USD: {stats.get('usd', 0):.4f}\n"
        )

    message = (
        "🔍 СРАВНЕНИЕ БАЗ ЗНАНИЙ\n\n"
        f"{format_block('Активная база', active)}\n"
        f"{format_block('Новая база', new)}\n"
        f"{format_block('Резервная копия', backup)}\n"
    )

    await update.message.reply_text(message)

    return

# ======================================================
# Сборка новой базы знаний через parser/build.py
# Вызывается только после подтверждения пользователя
# ======================================================


async def start_build_new_base(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """
    Собирает новую базу знаний через parser/build.py.

    Важно:
    База собирается в parser/output
    и не становится активной автоматически.
    """

    import asyncio
    import json
    from pathlib import Path

    progress_message = await update.message.reply_text(
        "🏗 Начинаю сборку новой базы знаний...\n\n"
        "⏳ Подготавливаю parser..."
    )

    try:

        parser_dir = (
            Path(__file__).resolve().parent.parent
            / "parser"
        )

        output_dir = parser_dir / "output"

        progress_file = output_dir / "progress.json"
        stats_file = output_dir / "build_stats.json"

        # очищаем старые файлы предыдущего запуска
        if progress_file.exists():
            progress_file.unlink()

        if stats_file.exists():
            stats_file.unlink()

        last_step = None

        current_url = context.bot_data.get(
            "rag_source_url",
            os.getenv(
                "RAG_SOURCE_URL",
                "https://professional24.ru"
            )
        )

        env = os.environ.copy()
        env["RAG_SOURCE_URL"] = current_url

        uv_path = shutil.which("uv")

        if uv_path is None:
            raise FileNotFoundError(
                "Не найден uv. Установите uv или добавьте его в PATH."
            )

        process = await asyncio.create_subprocess_exec(
            uv_path,
            "run",
            "build.py",
            cwd=str(parser_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # пока parser работает
        while True:

            # процесс завершился
            if process.returncode is not None:
                break

            # появился новый статус
            if progress_file.exists():

                try:

                    with open(
                        progress_file,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        progress_data = json.load(f)

                    current_step = progress_data.get("step")

                    if current_step != last_step:

                        await progress_message.edit_text(
                            "🏗 Сборка базы знаний\n\n"
                            f"{progress_data.get('progress', 0)}%\n\n"
                            f"{progress_data.get('message', 'Работаю...')}"
                        )

                        last_step = current_step

                except Exception:
                    pass

            await asyncio.sleep(2)

            if process.returncode is not None:
                break

        stdout, stderr = await process.communicate()

        # успешно завершилось
        if process.returncode == 0:

            stats = {}

            if stats_file.exists():

                with open(
                    stats_file,
                    "r",
                    encoding="utf-8"
                ) as f:
                    stats = json.load(f)

            await progress_message.edit_text(
                "✅ Новая база успешно собрана.\n\n"

                f"📄 Страниц: {stats.get('pages', 0)}\n"
                f"🧱 Блоков: {stats.get('blocks', 0)}\n"
                f"📦 Чанков: {stats.get('chunks', 0)}\n"
                f"🧠 Токенов: {stats.get('tokens', 0)}\n\n"

                f"💵 Стоимость:\n"
                f"USD: ${stats.get('usd', 0):.4f}\n"
                f"RUB: {stats.get('rub', 0):.2f} ₽\n\n"

                "📂 База сохранена в:\n"
                "parser/output/\n\n"

                "🟡 База собрана, но пока не активирована.\n\n"

                "Для применения используйте:\n"
                "🔄 Активировать новую базу"
            )

            # Возвращаем пользователя обратно
            # в меню управления базой знаний
            await show_knowledge_base_menu(
                update,
                context
            )

        else:

            stderr_text = stderr.decode(
                errors="ignore"
            ) if stderr else "Неизвестная ошибка"

            await progress_message.edit_text(
                "❌ Ошибка сборки базы.\n\n"
                f"{stderr_text[-3000:]}"
            )

    except Exception as e:

        await progress_message.edit_text(
            f"❌ Ошибка запуска сборки:\n\n{e}"
        )


# ======================================================
# Активирует новую базу знаний
# ======================================================
async def handle_activate_new_base(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    from services.knowledge_base_manager import (
        activate_new_base
    )

    await update.message.reply_text(
        "🔄 Начинаю активацию новой базы..."
    )

    success = activate_new_base()

    if success:

        # --------------------------------------------------
        # Перезагружаем индекс RAG в памяти бота
        # --------------------------------------------------
        from services.rag_service import (
            reload_rag_index
        )

        reload_success = reload_rag_index()

        if reload_success:

            await update.message.reply_text(
                "✅ Новая база успешно активирована.\n\n"
                "♻️ RAG индекс успешно перезагружен.\n"
                "📦 Предыдущая версия сохранена в резервной копии."
            )

        else:

            await update.message.reply_text(
                "⚠️ Новая база скопирована на диск,\n"
                "но не удалось перезагрузить RAG индекс.\n\n"
                "Рекомендуется перезапустить бота "
                "или выполнить откат базы."
            )


async def handle_knowledge_status(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """
    Показывает состояние всех баз знаний.
    """

    from services.knowledge_base_manager import (
        get_knowledge_base_status
    )

    status = get_knowledge_base_status()

    text = "📊 Статус базы знаний\n\n"

    # ==========================================
    # Активная база
    # ==========================================
    if status.get("active"):

        active = status["active"]

        text += (
            "🟢 Активная база\n"
            f"📄 Страниц: {active.get('pages', 0)}\n"
            f"📦 Чанков: {active.get('chunks', 0)}\n"
            f"🧠 Токенов: {active.get('tokens', 0)}\n"
            f"🕒 Активирована: "
            f"{active.get('created_at', 'неизвестно')}\n\n"
        )

    else:

        text += (
            "🔴 Активная база отсутствует\n\n"
        )

    # ==========================================
    # Новая база
    # ==========================================
    if status.get("new"):

        new = status["new"]

        text += (
            "🟡 Новая собранная база\n"
            f"📄 Страниц: {new.get('pages', 0)}\n"
            f"📦 Чанков: {new.get('chunks', 0)}\n"
            f"🧠 Токенов: {new.get('tokens', 0)}\n"
            f"🕒 Собрана: "
            f"{new.get('created_at', 'неизвестно')}\n"
            f"Статус: ожидает активации\n\n"
        )

    else:

        text += (
            "⚪ Новая база отсутствует\n\n"
        )

    # ==========================================
    # Backup
    # ==========================================
    if status.get("backup"):

        backup = status["backup"]

        text += (
            "💾 Резервная копия\n"
            f"📄 Страниц: {backup.get('pages', 0)}\n"
            f"📦 Чанков: {backup.get('chunks', 0)}\n"
            f"🧠 Токенов: {backup.get('tokens', 0)}\n"
            f"🕒 Создана: "
            f"{backup.get('created_at', 'неизвестно')}\n"
            f"Статус: готова к откату"
        )

    else:

        text += (
            "💾 Резервная копия отсутствует"
        )

    await update.message.reply_text(text)


# ======================================================
# Откат базы знаний на предыдущую рабочую версию
# ======================================================
async def handle_backup_restore(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """
    Выполняет откат активной базы знаний
    на предыдущую рабочую версию.

    После восстановления автоматически
    выполняется reload RAG индекса.
    """

    from services.knowledge_base_manager import (
        rollback_to_backup
    )

    from services.rag_service import (
        reload_rag_index
    )

    await update.message.reply_text(
        "⏪ Начинаю восстановление предыдущей базы..."
    )

    success = rollback_to_backup()

    if not success:

        await update.message.reply_text(
            "❌ Не удалось восстановить резервную копию.\n\n"
            "Проверьте логи сервера."
        )

        return

    # -----------------------------------------
    # Перезагрузка FAISS после отката
    # -----------------------------------------
    reload_success = reload_rag_index()

    if reload_success:

        await update.message.reply_text(
            "✅ Предыдущая версия базы успешно восстановлена.\n\n"
            "♻️ RAG индекс успешно перезагружен."
        )

    else:

        await update.message.reply_text(
            "⚠️ База восстановлена, "
            "но возникла ошибка перезагрузки RAG индекса.\n\n"
            "Рекомендуется перезапустить бота."
        )


async def save_rag_source_url(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    new_url = update.message.text.strip()

    if not new_url.startswith(("http://", "https://")):
        new_url = "https://" + new_url

    # пока просто сохраняем в память бота
    context.bot_data["rag_source_url"] = new_url

    settings_path = (
        Path(__file__).resolve().parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )

    with open(
        settings_path,
        "r",
        encoding="utf-8"
    ) as f:
        settings = json.load(f)

    settings["base_url"] = new_url

    with open(
        settings_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=4
        )

    await update.message.reply_text(
        f"✅ Новый источник знаний сохранён:\n\n"
        f"{new_url}",
        reply_markup=get_knowledge_base_keyboard()
    )

    return ConversationHandler.END


# ======================================================
# Сохраняет новый лимит страниц для парсера.
#
# Пользователь вводит:
# 10 -> парсим 10 страниц
# 100 -> парсим 100 страниц
# 0 -> парсим весь сайт без ограничений
# ======================================================
async def save_crawl_limit(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    try:
        # преобразуем текст пользователя в число
        new_limit = int(
            update.message.text.strip()
        )

        # отрицательные значения запрещаем
        if new_limit < 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Введите число больше либо равное нулю."
        )

        return AWAITING_CRAWL_LIMIT

    # путь к динамическим настройкам parser
    settings_path = (
        Path(__file__).resolve().parent.parent
        / "parser"
        / "app"
        / "config"
        / "settings.json"
    )

    # читаем текущие настройки
    with open(
        settings_path,
        "r",
        encoding="utf-8"
    ) as f:
        settings = json.load(f)

    # сохраняем новый лимит страниц
    settings["crawl_limit"] = new_limit

    # записываем изменения обратно в файл
    with open(
        settings_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            settings,
            f,
            ensure_ascii=False,
            indent=4
        )

    # Для пользователя показываем более понятное значение
    display_limit = (
        "Все страницы"
        if new_limit == 0
        else str(new_limit)
    )

    await update.message.reply_text(
        f"✅ Новый лимит страниц сохранён:\n\n"
        f"{display_limit}",
        reply_markup=get_knowledge_base_keyboard()
    )

    return ConversationHandler.END


# ==========================================================
# РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ АДМИНИСТРАТИВНОЙ ПАНЕЛИ
# ==========================================================


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
            handle_call_request,
            pattern=r"^call_\d+$"
        ),
        CallbackQueryHandler(
            handle_chat_navigation,
            pattern=r"^chat_page_\d+$"
        ),
        CallbackQueryHandler(
            handle_chat_navigation,
            pattern=r"^back_to_users$"
        ),
        CallbackQueryHandler(
            handle_chat_navigation,
            pattern=r"^(chat_page_|back_to_users)$"
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
            filters.Text(btn.BTN_ACTIVATE_NEW_BASE),
            handle_activate_new_base
        ),
        MessageHandler(
            filters.Text(btn.BTN_BACKUP),
            handle_backup_restore
        ),

        MessageHandler(
            filters.Text(btn.BTN_KNOWLEDGE_STATUS),
            handle_knowledge_status
        ),

        # CallbackQuery
        *callback_handlers,
    ]
