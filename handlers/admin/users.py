"""
handlers/admin/users.py

Управление пользователями административной панели.

Модуль отвечает за:

- отображение списка пользователей с пагинацией;
- поиск клиентов;
- просмотр карточки пользователя с inline-кнопками;
- просмотр истории переписки с пагинацией;
- прямой ответ клиенту из админки;
- запрос на звонок клиенту.
"""

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import buttons as btn
from config.admin_keyboards import get_admin_keyboard
from config.keyboards import get_cancel_keyboard

from database import (
    add_message,
    get_client_info,
    get_clients_paginated,
    get_paginated_messages,
    get_total_clients_count,
    get_total_messages_count,
    mark_user_blocked,
    search_clients,
)

from handlers.admin.constants import (
    AWAITING_MESSAGE_TO_CLIENT,
    AWAITING_SEARCH_QUERY,
    PAGE_SIZE,
)

logger = logging.getLogger(__name__)


# ==========================================================
# Форматирование карточки клиента.
# ==========================================================

def format_client(client: dict) -> tuple[str, InlineKeyboardMarkup]:
    """
    Формирует красивую карточку клиента
    и inline-клавиатуру для быстрых действий.

    Показывает основную информацию о пользователе
    и кнопки: История, Написать, Звонок (если есть телефон).

    Returns:
        tuple: Текст карточки и объект InlineKeyboardMarkup.
    """

    name_parts = []
    if client.get('first_name'):
        name_parts.append(client['first_name'])
    if client.get('last_name'):
        name_parts.append(client['last_name'])
    name = ' '.join(name_parts) or "Без имени"
    
    username = f"@{client['username']}" if client['username'] else "—"
    phone = client['phone'] or "—"
    
    # Форматирование даты регистрации
    date_str = client['joined_at'][:10] if client['joined_at'] else "—"
    if date_str != "—":
        try:
            d = date_str.split('-')
            date_str = f"{d[2]}.{d[1]}.{d[0]}"
        except Exception:
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
        InlineKeyboardButton("💬 История", callback_data=f"chat_{client['user_id']}"),
        InlineKeyboardButton("📨 Написать", callback_data=f"write_{client['user_id']}")
    ]
    
    if client.get('phone'):
        buttons.append(InlineKeyboardButton("📞 Звонок", callback_data=f"call_{client['user_id']}"))

    return text, InlineKeyboardMarkup([buttons])


# ==========================================================
# Поиск пользователей.
# ==========================================================

async def start_client_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Переводит администратора в режим поиска пользователей.
    Следующий текст считается поисковым запросом.

    Returns:
        int: Состояние AWAITING_SEARCH_QUERY.
    """

    await update.message.reply_text(
        "🔍 Введите запрос для поиска:\n"
        "• Телефон (от 4 цифр)\n• Username (от 3 символов)\n• Имя/фамилия (от 5 букв)\n\n"
        "Нажмите «⬅❌ Отмена», чтобы выйти.",
        reply_markup=get_cancel_keyboard()
    )

    return AWAITING_SEARCH_QUERY


async def handle_search_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Выполняет поиск пользователей по введённому запросу.
    Выводит до 10 найденных клиентов с inline-кнопками.

    Returns:
        int: Конец диалога (ConversationHandler.END).
    """

    text = update.message.text.strip()
    
    if text == btn.BTN_CANCEL:
        await update.message.reply_text("Поиск отменён.", reply_markup=get_admin_keyboard())
        return ConversationHandler.END

    clients = search_clients(text)

    if not clients:
        await update.message.reply_text(
            f"❌ Ничего не найдено по запросу:\n«{text}»",
            reply_markup=get_admin_keyboard(),
        )
        return ConversationHandler.END

    # Показываем до 10 клиентов
    for client in clients[:10]:
        client_text, inline_keyboard = format_client(client)
        await update.message.reply_text(client_text, reply_markup=inline_keyboard)

    summary = (
        f"✅ Найдено {len(clients)} клиент(а/ов)." 
        if len(clients) <= 10 else 
        f"✅ Найдено {len(clients)} клиентов (показаны первые 10)."
    )
    
    await update.message.reply_text(summary, reply_markup=get_admin_keyboard())
    return ConversationHandler.END


async def cancel_search(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Отменяет поиск пользователей и возвращает в админку.

    Returns:
        int: Конец диалога (ConversationHandler.END).
    """

    del context

    await update.message.reply_text(
        "❌ Поиск отменён.",
        reply_markup=get_admin_keyboard(),
    )

    return ConversationHandler.END


# ==========================================================
# Звонок клиенту.
# ==========================================================

def format_phone_for_display(phone: str) -> str:
    """Приводит номер телефона к формату +7 (XXX) XXX-XX-XX."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return phone


async def handle_call_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Показывает администратору данные для звонка клиенту
    и отправляет клиенту уведомление о предстоящем звонке.
    """

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
    except Exception:
        notified = False

    display_phone = format_phone_for_display(phone)
    username = client_info.get('username')
    name = f"{client_info['first_name'] or ''} {client_info['last_name'] or ''}".strip() or "Без имени"
    
    parts = [f"📞 <b>Перезвонить клиенту</b>:\n• Имя: {name}"]
    if username:
        parts.append(f'• <a href="tg://resolve?domain={username}">:@{username}</a>')
    else:
        parts.append("• @username: —")
        
    parts.append(f'• Телефон: <a href="tel:+{raw_phone}">{display_phone}</a>')
    parts.append(f"• ID: <code>{user_id}</code>")
    parts.append(f"{'✅ Клиент уведомлён' if notified else '⚠️ Не уведомлён'}")

    await query.message.reply_text(
        "\n".join(parts),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


# ==========================================================
# Прямой ответ клиенту.
# ==========================================================

async def start_write_to_client(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Запускает режим отправки сообщения конкретному клиенту.
    Вызывается через inline-кнопку "📨 Написать".

    Returns:
        int: Состояние AWAITING_MESSAGE_TO_CLIENT или конец диалога.
    """

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

    name = (client_info['first_name'] or '') + (' ' + (client_info['last_name'] or ''))
    name = name.strip() or "Клиент"
    username = client_info.get('username')
    target = (
        f'<a href="tg://resolve?domain={username}">@{username}</a>' 
        if username else f"ID: <code>{user_id}</code>"
    )

    await query.message.reply_text(
        f"✏️ Введите сообщение для {target}:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_MESSAGE_TO_CLIENT


async def send_message_to_client(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """
    Отправляет введённое администратором сообщение клиенту.

    Returns:
        int: Конец диалога (ConversationHandler.END).
    """

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
        await update.message.reply_text(
            "❌ Не удалось отправить. Возможно, клиент заблокировал бота.",
            reply_markup=get_admin_keyboard()
        )
        context.user_data.pop('writing_to', None)
        return ConversationHandler.END

    client_info = get_client_info(user_id)
    name = (
        (client_info['first_name'] or '') + (' ' + (client_info['last_name'] or ''))
        if client_info else ""
    )
    name = name.strip() or "Клиент"
    username = client_info.get('username') if client_info else None
    target = (
        f'<a href="tg://resolve?domain={username}">@{username}</a>'
        if username else f"ID: <code>{user_id}</code>"
    )

    context.user_data.pop('writing_to', None)
    await update.message.reply_text(
        f"✅ Сообщение отправлено {target}!",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    return ConversationHandler.END


async def cancel_write_to_client(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Отменяет режим написания сообщения клиенту."""
    context.user_data.pop('writing_to', None)
    await update.message.reply_text("Отменено.", reply_markup=get_admin_keyboard())
    return ConversationHandler.END


# ==========================================================
# Отображение списка пользователей.
# ==========================================================

async def show_users_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 0,
) -> None:
    """
    Показывает страницу списка пользователей.
    Отправляет каждого клиента отдельным сообщением с inline-кнопками.
    В конце отправляет панель навигации между страницами.
    """

    offset = page * PAGE_SIZE
    clients = get_clients_paginated(offset=offset, limit=PAGE_SIZE)
    total = get_total_clients_count()

    if not clients:
        text = "📭 Нет зарегистрированных пользователей."
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 В админку", callback_data="users_back")]]
        )
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(text, reply_markup=keyboard)
        return

    # Определяем, куда отправлять сообщения (CallbackQuery или обычное сообщение)
    target = update.callback_query.message if update.callback_query else update.message

    # Отправляем каждого клиента отдельным сообщением
    for client in clients:
        client_text, inline_keyboard = format_client(client)
        await target.reply_text(client_text, reply_markup=inline_keyboard)

    # Формируем навигацию в последнем сообщении
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(btn.BTN_PREVIOUS, callback_data=f"users_page_{page - 1}"))
        
    if len(clients) == PAGE_SIZE and (page + 1) * PAGE_SIZE < total:
        nav_buttons.append(InlineKeyboardButton("Далее ➡️", callback_data=f"users_page_{page + 1}"))

    if nav_buttons:
        nav_keyboard = InlineKeyboardMarkup([nav_buttons])
        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        summary_text = f"👥 Страница {page + 1} из {total_pages}"
        await target.reply_text(summary_text, reply_markup=nav_keyboard)
    else:
        await target.reply_text("✅ Конец списка.")
        

async def handle_users_navigation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обрабатывает переключение страниц списка пользователей
    через inline-кнопки (CallbackQuery).
    """

    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("users_page_"):
        try:
            page = int(data.split("_")[2])
            await show_users_page(update, context, page=page)
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Ошибка навигации.")
    elif data == "users_back":
        # Возврат обработывается в основном роутере или тут заглушка
        pass
    else:
        await query.message.reply_text("Неизвестное действие.")


# ==========================================================
# Просмотр истории переписки.
# ==========================================================

async def show_chat_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Открывает историю переписки выбранного пользователя.
    Вызывается через inline-кнопку "💬 История".
    """

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


async def show_chat_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    page: int = 0,
) -> None:
    """
    Показывает страницу истории переписки клиента.
    Обновляет сообщение через edit_message_text.
    """

    query = update.callback_query
    user_id = context.user_data.get('viewing_chat_of')
    
    if not user_id:
        await query.message.reply_text("❌ Ошибка: не указан клиент.")
        return

    offset = page * PAGE_SIZE
    messages = get_paginated_messages(user_id, offset=offset, limit=PAGE_SIZE)
    total_msgs = get_total_messages_count(user_id)

    if not messages:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(btn.BTN_PREVIOUS, callback_data="back_to_users")]]
        )
        await query.edit_message_text("📭 Нет сообщений.", reply_markup=keyboard)
        return

    # Получаем имя клиента
    client_info = get_client_info(user_id)
    if client_info:
        name_parts = []
        if client_info.get('first_name'):
            name_parts.append(client_info['first_name'])
        if client_info.get('last_name'):
            name_parts.append(client_info['last_name'])
        display_name = ' '.join(name_parts) or f"ID {user_id}"
        username = f" (@{client_info['username']})" if client_info.get('username') else ""
    else:
        display_name = f"ID {user_id}"
        username = ""

    history = f"💬 Переписка с {display_name}{username} (стр. {page + 1}):\n\n"
    
    for msg in messages:
        role = "👤 Клиент" if msg['role'] == 'user' else "🤖 Бот"
        content = (msg['content'][:200] + '...') if len(msg['content']) > 200 else msg['content']
        ts = msg['timestamp'][:16] if msg['timestamp'] else "—"
        history += f"{role} ({ts}):\n{content}\n\n"

    # Кнопки навигации по истории
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(btn.BTN_PREVIOUS, callback_data=f"chat_page_{page - 1}"))
    if len(messages) == PAGE_SIZE and (page + 1) * PAGE_SIZE < total_msgs:
        nav_buttons.append(InlineKeyboardButton("Далее ➡️", callback_data=f"chat_page_{page + 1}"))

    nav_buttons.append(InlineKeyboardButton("🏠 К списку", callback_data="back_to_users"))
    keyboard = InlineKeyboardMarkup([nav_buttons])

    await query.edit_message_text(history, reply_markup=keyboard)


async def handle_chat_navigation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обрабатывает переключение страниц истории переписки
    через inline-кнопки (CallbackQuery).
    """

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_users":
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
