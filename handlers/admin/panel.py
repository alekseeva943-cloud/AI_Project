"""
handlers/admin/panel.py

Главная административная панель.

Модуль отвечает за:
- открытие админ-панели;
- главное меню администратора;
- переходы между разделами;
- отображение основных экранов управления.

Является центральным роутером (маршрутизатором) для команд администратора.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import buttons as btn
from config.config import is_admin as is_admin_user

from config.admin_keyboards import (
    get_admin_keyboard,
    get_knowledge_base_keyboard,
    get_settings_keyboard,
)

# Импорты обработчиков разбитых по модулям
from handlers.admin.stats import handle_stats_period, handle_top_requests_period
from handlers.admin.stats import (
    handle_stats_period,
    handle_top_requests_period,
    show_stats_menu,
    show_top_requests_menu,
)

from handlers.admin.users import show_users_page
from handlers.utilities.menu import go_back

# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Проверка прав и отображение меню
# ==========================================================

async def check_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Проверяет, является ли пользователь администратором.

    Если пользователь имеет права и еще не видел приветствие 
    админ-панели в текущей сессии, отправляет приветственное сообщение 
    и ставит флаг в user_data, чтобы не спамить при каждом сообщении.

    Args:
        update: Объект входящего обновления Telegram.
        context: Контекст беседы (для доступа к user_data).

    Returns:
        bool: True, если пользователь админ, иначе False.
    """

    user = update.effective_user
    admin = is_admin_user(user.id)

    if (
        admin
        and not context.user_data.get(
            "admin_panel_shown"
        )
    ):
        await update.message.reply_text(
            "🛠 Добро пожаловать в админ-панель",
            reply_markup=get_admin_keyboard(),
        )

        context.user_data[
            "admin_panel_shown"
        ] = True

    return admin


async def show_settings_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Открывает раздел настроек административной панели.

    Сохраняет текущее состояние в 'previous_state' 
    для корректной работы универсальной кнопки "Назад".
    """

    context.user_data[
        "previous_state"
    ] = "settings_menu"

    await update.message.reply_text(
        "⚙️ Настройки:",
        reply_markup=get_settings_keyboard(),
    )


async def show_knowledge_base_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Открывает меню управления базой знаний (RAG).

    Сохраняет текущее состояние в 'previous_state' 
    для корректной работы кнопки "Назад".
    """

    context.user_data[
        "previous_state"
    ] = "knowledge_base_menu"

    await update.message.reply_text(
        btn.BTN_KNOWLEDGE_BASE,
        reply_markup=get_knowledge_base_keyboard(),
    )


async def show_admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Показывает главное меню административной панели.

    Запоминает предыдущее состояние пользователя, 
    чтобы при выходе из админки вернуть его туда же, 
    откуда он пришел (например, в 'main_menu').
    """

    if (
        context.user_data.get(
            "previous_state"
        )
        != "admin_panel"
    ):

        context.user_data[
            "return_to_after_admin"
        ] = context.user_data.get(
            "previous_state",
            "main_menu",
        )

    context.user_data[
        "previous_state"
    ] = "admin_panel"

    await update.message.reply_text(
        "🛠 Админ-панель:",
        reply_markup=get_admin_keyboard(),
    )


# ==========================================================
# Центральный роутер админки
# ==========================================================

async def handle_admin_actions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Центральный обработчик нажатий кнопок административной панели.

    Проверяет права администратора и перенаправляет 
    нажатия текстовых кнопок в соответствующие разделы:
    - Статистика (Топ запросов / Статистика проекта)
    - Настройки
    - Пользователи
    - Обработка выбора периодов для статистики
    - Навигация (Назад / Отмена)
    """

    if not await check_admin(
        update,
        context,
    ):
        return

    text = update.message.text

    # ======================================================
    # Главное меню.
    # ======================================================

    if text == btn.BTN_STATS:
        # Переход к выбору периода для Топ запросов
        await show_top_requests_menu(
            update,
            context,
        )

    elif text == btn.BTN_TOP_REQUESTS:
        # Переход к выбору периода для Статистики проекта
        await show_stats_menu(
            update,
            context,
        )

    elif text == btn.BTN_SETTINGS:
        logger.info(
            "Открытие меню настроек."
        )

        await show_settings_menu(
            update,
            context,
        )

    elif text == btn.BTN_USERS:
        # Открывает первую страницу (page=0) списка пользователей
        await show_users_page(
            update,
            context,
            page=0,
        )

    # ======================================================
    # Навигация.
    # ======================================================

    elif text in (
        btn.BTN_BACK,
        btn.BTN_PREVIOUS,
        btn.BTN_CANCEL,
    ):
        # Универсальный возврат на предыдущий экран
        await go_back(
            update,
            context,
        )

    # ======================================================
    # Статистика (обработка выбранных периодов).
    # ======================================================

    elif text in (
        btn.BTN_TODAY,
        btn.BTN_WEEK,
        btn.BTN_MONTH,
        btn.BTN_STATS_YEAR,
    ):
        # Формирует и отправляет отчет по статистике проекта
        await handle_stats_period(
            update,
            context,
            text,
        )

    elif text in (
        btn.BTN_PERIOD_7_DAYS,
        btn.BTN_PERIOD_30_DAYS,
        btn.BTN_PERIOD_HALF_YEAR,
        btn.BTN_PERIOD_YEAR,
    ):
        # Формирует и отправляет отчет по топу запросов
        await handle_top_requests_period(
            update,
            context,
            text,
        )

    # ======================================================
    # Неизвестная команда.
    # ======================================================

    else:

        await update.message.reply_text(
            "❓ Неизвестная команда"
        )