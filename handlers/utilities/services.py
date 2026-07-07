# handlers/utilities/services.py

"""
Работа с услугами компании.

Содержит отображение основных услуг,
автопомощи, контактов и меню помощи.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import buttons as btn
from config.keyboards import (
    get_auto_help_keyboard,
    get_back_keyboard,
    get_contact_keyboard,
    get_help_keyboard,
    get_services_keyboard,
)
from prompts.service_prompts import (
    AUTO_HELP_PROMPTS,
    HELP_PROMPTS,
    SERVICES_PROMPTS,
)

from database import add_message


logger = logging.getLogger(__name__)


# ==========================================================
# Меню услуг.
# ==========================================================

async def handle_services(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает меню услуг компании.

    Returns:
        None.
    """

    context.user_data["previous_state"] = "main_menu"

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_services_keyboard(),
    )


# ==========================================================
# Основные услуги.
# ==========================================================

async def show_service_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает описание
    выбранной услуги.

    Returns:
        None.
    """

    from .menu import show_main_menu

    service = update.message.text

    if service == btn.BTN_BACK:
        await show_main_menu(update, context)
        return

    text = SERVICES_PROMPTS.get(service)

    if not text:
        logger.warning(
            f"Не найдено описание услуги: {service}"
        )
        return

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard(),
    )


# ==========================================================
# Авто-помощь.
# ==========================================================

async def show_auto_help_submenu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает меню
    услуг автопомощи.

    Returns:
        None.
    """

    context.user_data["previous_state"] = "services_menu"

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_auto_help_keyboard(),
    )


async def show_auto_help_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает описание
    выбранной услуги автопомощи.

    Returns:
        None.
    """

    service = update.message.text

    if service == btn.BTN_BACK:
        await handle_services(update, context)
        return

    text = AUTO_HELP_PROMPTS.get(service)

    if not text:
        logger.warning(
            f"Не найдено описание автопомощи: {service}"
        )
        return

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard(),
    )


# ==========================================================
# Меню помощи.
# ==========================================================

async def handle_help_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает ответ
    на выбранную проблему.

    Returns:
        None.
    """

    context.user_data["previous_state"] = "help_menu"

    choice = update.message.text

    text = HELP_PROMPTS.get(choice)

    if not text:
        return

    add_message(
        update.effective_user.id,
        "user",
        choice,
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_contact_keyboard(),
    )


# ==========================================================
# Контакты компании.
# ==========================================================

async def show_contacts(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Показывает контактную
    информацию компании.

    Returns:
        None.
    """

    context.user_data["previous_state"] = "main_menu"

    await update.message.reply_contact(
        phone_number="+74952369990",
        first_name="Professional24",
        last_name="Сервис",
    )

    await update.message.reply_text(
        "📞 Телефон: +7 495 236-99-90\n"
        "🌐 Сайт: https://professional24.ru/\n\n"
        "Работаем круглосуточно 🚗",
        reply_markup=get_back_keyboard(),
    )