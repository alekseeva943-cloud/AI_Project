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

from handlers.admin.stats import (
    handle_stats_period,
    handle_top_requests_period,
    show_stats_menu,
    show_top_requests_menu,
)

from handlers.admin.users import show_users_page
from handlers.utilities.menu import show_main_menu
from handlers.utilities.nav_stack import push_state, clear_stack
from handlers.utilities.navigation import navigate_back

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
    """
    user = update.effective_user
    admin = is_admin_user(user.id)

    if (
        admin
        and not context.user_data.get("admin_panel_shown")
    ):
        await update.message.reply_text(
            "🛠 Добро пожаловать в админ-панель",
            reply_markup=get_admin_keyboard(),
        )
        context.user_data["admin_panel_shown"] = True

    return admin


async def show_settings_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Открывает раздел настроек.
    Сохраняет ТЕКУЩЕЕ состояние (админ-панель) перед переходом.
    """
    push_state(context, "admin_panel")
    
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
    
    Отвечает за:
    - отображение клавиатуры управления базой знаний;
    - сохранение точки возврата в стек навигации.

    Что делает:
    Так как этот раздел доступен ТОЛЬКО из меню "Настройки", 
    мы жестко сохраняем "settings_menu" в стек. 
    Благодаря этому кнопка "Назад" внутри базы знаний 
    всегда будет возвращать именно в Настройки, а не перескакивать в корень.
    """
    from handlers.utilities.nav_stack import push_state

    push_state(context, "settings_menu")

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
    """
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
    """
    if not await check_admin(update, context):
        return

    text = update.message.text

    # ======================================================
    # Главное меню — переходы в подменю
    # ======================================================

    if text == btn.BTN_STATS:
        push_state(context, "admin_panel")
        await show_top_requests_menu(update, context)

    elif text == btn.BTN_TOP_REQUESTS:
        push_state(context, "admin_panel")
        await show_stats_menu(update, context)

    elif text == btn.BTN_SETTINGS:
        logger.info("Открытие меню настроек.")
        await show_settings_menu(update, context)

    elif text == btn.BTN_USERS:
        push_state(context, "admin_panel")
        await show_users_page(update, context, page=0)

    # ======================================================
    # Навигация — универсальная обработка
    # ======================================================

    elif text in (btn.BTN_BACK, btn.BTN_PREVIOUS, btn.BTN_CANCEL):
        await navigate_back(update, context)

    # ======================================================
    # Статистика (обработка выбранных периодов)
    # ======================================================

    elif text in (
        btn.BTN_TODAY,
        btn.BTN_WEEK,
        btn.BTN_MONTH,
        btn.BTN_STATS_YEAR,
    ):
        await handle_stats_period(update, context, text)

    elif text in (
        btn.BTN_PERIOD_7_DAYS,
        btn.BTN_PERIOD_30_DAYS,
        btn.BTN_PERIOD_HALF_YEAR,
        btn.BTN_PERIOD_YEAR,
    ):
        await handle_top_requests_period(update, context, text)

    # ======================================================
    # Неизвестная команда
    # ======================================================

    else:
        await update.message.reply_text("❓ Неизвестная команда")