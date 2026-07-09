# handlers/admin_management.py

from telegram import Update
from telegram.ext import ContextTypes
from config.admin_keyboards import get_admins_management_keyboard
from config.config import SUPERADMIN_ID
from config.keyboards import get_cancel_keyboard
from database import get_all_admins, add_admin, remove_admin, DB_PATH
from handlers.utilities.nav_stack import push_state

import logging

logger = logging.getLogger(__name__)


async def show_admins_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отображает экран управления администраторами.

    Отвечает за:
    - проверку прав доступа (доступно только суперадмину);
    - формирование читаемого списка текущих администраторов с указанием их ролей;
    - вывод клавиатуры для добавления или удаления админов.

    Что делает:
    Запрашивает из БД список админов, помечает суперадмина спецсимволом 
    для визуального отличия и отправляет результат пользователю.

    Важно по навигации: 
    Эта функция НЕ сохраняет состояние в стек навигации (не вызывает push_state). 
    Сохранение состояния происходит в момент перехода (в handlers.py), 
    чтобы избежать дублирования состояний при возврате сюда из сценариев отмены.
    """
    user_id = update.effective_user.id
    
    # Защита от несанкционированного доступа
    if user_id != SUPERADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    admins = get_all_admins(DB_PATH)
    
    if not admins:
        text = "📭 Список админов пуст."
    else:
        lines = []
        for a in admins:
            # Склеиваем имя и фамилию, убирая лишние пробелы. Если нет ничего — ставим прочерк.
            name = f"{a['first_name'] or ''} {a['last_name'] or ''}".strip() or "—"
            username = f"@{a['username']}" if a['username'] else "—"
            
            # Визуально разделяем суперадмина и обычных админов
            marker = "👑" if a['user_id'] == SUPERADMIN_ID else "👤"
            lines.append(
                f"{marker} {name}\n   ID: {a['user_id']} | {username}"
            )
        text = "👥 Список админов:\n\n" + "\n\n".join(lines)

    await update.message.reply_text(
        text,
        reply_markup=get_admins_management_keyboard()
    )
    
    # Старая строка context.user_data['previous_state'] = 'settings_menu' 
    # удалена намеренно. Навигация теперь управляется стеком из handlers.py

async def add_admin_start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """
    Запускает сценарий (ConversationHandler) добавления нового администратора.

    Отвечает за:
    - проверку прав суперадмина на запуск сценария;
    - настройку безопасного выхода из сценария по кнопке "Отмена";
    - запрос у пользователя идентификатора нового админа.

    Что делает:
    Сохраняет в контекст функцию-точку возврата (cancel_target) и 
    устанавливает флаг ожидаемого действия, чтобы следующий обработчик 
    понял, что нужно делать с полученным текстом.
    """
    if update.effective_user.id != SUPERADMIN_ID:
        return

    # Указываем функции отмены (cancel_current_action в menu.py), 
    # куда именно нужно вернуть пользователя при нажатии "Отмена".
    # Передаём саму функцию, а не строку, чтобы бот напрямую вызвался нужный экран.
    context.user_data["cancel_target"] = show_admins_menu

    await update.message.reply_text(
        "Введите ID или username (например: 123456789 или @Al_leks):",
        reply_markup=get_cancel_keyboard()
    )

    # Флаг для следующего шага (handle_admin_input), 
    # чтобы понять, что мы именно добавляем, а не удаляем админа.
    context.user_data["awaiting_action"] = "add_admin"

    return 1


async def remove_admin_start(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):
    """
    Запускает сценарий (ConversationHandler) удаления администратора.

    Отвечает за:
    - проверку прав суперадмина;
    - фильтрацию списка админов (исключение суперадмина, так как его удалять нельзя);
    - вывод доступных для удаления ID;
    - настройку безопасного выхода по кнопке "Отмена".

    Что делает:
    Получает список админов, отсекает оттуда суперадмина для безопасности. 
    Если удалять некого — прерывает сценарий. Если есть кандидаты — 
    показывает их ID и просит ввести нужный для удаления.
    """
    if update.effective_user.id != SUPERADMIN_ID:
        return

    admins = get_all_admins(DB_PATH)
    
    # Формируем список админов, которых МОЖНО удалить (исключаем суперадмина ради безопасности)
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

    # Настройка возврата при отмене (аналогично add_admin_start)
    context.user_data["cancel_target"] = show_admins_menu

    # Собираем только ID в строку для подсказки пользователю
    ids = "\n".join(
        str(admin["user_id"])
        for admin in non_super
    )

    await update.message.reply_text(
        f"Введите ID администратора для удаления:\n\n"
        f"Доступные ID:\n{ids}",
        reply_markup=get_cancel_keyboard()
    )

    # Флаг для следующего шага: сигнализируем, что нужно именно УДАЛИТЬ
    context.user_data["awaiting_action"] = "remove_admin"

    return 1

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик введённых данных для сценариев добавления/удаления админов.

    Отвечает за:
    - определение формата ввода (числовой ID или текстовый username);
    - запрос данных о пользователе напрямую из Telegram API;
    - валидацию введённых данных;
    - выполнение финального действия (запись в БД или удаление).

    Что делает:
    Читает флаг 'awaiting_action', чтобы понять, что именно делает пользователь. 
    Если это добавление — парсит ID/username, получает имя из Telegram и записывает в БД. 
    Если удаление — проверяет, что это не суперадмин, и удаляет из БД.
    """
    user = update.effective_user
    if user.id != SUPERADMIN_ID:
        return

    # Узнаём, на каком этапе мы находимся (добавление или удаление)
    action = context.user_data.get('awaiting_action')
    if not action:
        return

    text = update.message.text.strip()
    
    # Сразу сбрасываем флаг, чтобы обработчик не сработал повторно
    context.user_data['awaiting_action'] = None

    try:
        # ==================================================================
        # Логика ДОБАВЛЕНИЯ администратора
        # ==================================================================
        if action == 'add_admin':
            
            # Вариант 1: Пользователь ввел числовой ID
            if text.isdigit():
                admin_id = int(text)
                try:
                    # Запрашиваем у Telegram актуальные данные пользователя по ID
                    chat = await context.bot.get_chat(admin_id)
                    username = chat.username
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    # Если бот не имеет доступа к этому ID (например, заблокирован или не существует)
                    username = first_name = last_name = None
                    
            # Вариант 2: Пользователь ввел username, начинающийся с @
            elif text.startswith('@'):
                username = text[1:]
                try:
                    chat = await context.bot.get_chat(text)
                    admin_id = chat.id
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    await update.message.reply_text("❌ Не удалось найти пользователя по username.")
                    return
                    
            # Вариант 3: Пользователь ввел username без @ (запасной вариант)
            else:
                username = text
                try:
                    chat = await context.bot.get_chat(f"@{text}")
                    admin_id = chat.id
                    first_name = chat.first_name
                    last_name = chat.last_name
                except Exception:
                    await update.message.reply_text("❌ Не удалось найти пользователя по username.")
                    return

            # Финальная проверка безопасности: нельзя добавить суперадмина как обычного
            if admin_id == SUPERADMIN_ID:
                await update.message.reply_text("👑 Этот пользователь — суперадмин.")
            else:
                # Записываем нового админа в базу данных
                add_admin(DB_PATH, admin_id, username, first_name,
                          last_name, added_by=SUPERADMIN_ID)
                await update.message.reply_text(f"✅ Админ добавлен:\nID: {admin_id}\nUsername: @{username or '—'}")

        # ==================================================================
        # Логика УДАЛЕНИЯ администратора
        # ==================================================================
        elif action == 'remove_admin':
            # Удаление работает ТОЛЬКО по числовому ID для исключения ошибок
            if not text.isdigit():
                await update.message.reply_text("❌ Введите корректный ID (только цифры).")
                return
                
            admin_id = int(text)
            
            # Защита от удаления суперадмина (даже если кто-то подсунул его ID)
            if admin_id == SUPERADMIN_ID:
                await update.message.reply_text("❌ Нельзя удалить суперадмина.")
            else:
                remove_admin(DB_PATH, admin_id)
                await update.message.reply_text(f"🗑 Админ с ID {admin_id} удалён.")

    except Exception as e:
        # Логируем полную трассировку ошибки для дебага
        logger.error(f"Ошибка при управлении админом: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка при обработке. Проверьте данные и повторите.")