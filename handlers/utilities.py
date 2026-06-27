# utilities.py
# Файл отвечает за работу служебных меню, клавиатур, контактов,
# отображение услуг, автопомощи и регистрацию служебных обработчиков.

from prompts.service_prompts import (
    SERVICES_PROMPTS,
    AUTO_HELP_PROMPTS,
    HELP_PROMPTS
)
import logging

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config.keyboards import (
    get_services_keyboard,
    get_auto_help_keyboard,
    get_help_keyboard,
    get_contact_keyboard,
    get_back_keyboard
)

from config import is_admin, get_main_keyboard
from config.config import CONTEXT_MESSAGE_COUNT

from database import add_message, get_last_messages, DB_PATH
from config import buttons as btn

logger = logging.getLogger(__name__)


# =======================
# 🔹 МЕНЮ
# =======================

# Показывает главное меню бота и очищает временный GPT-контекст пользователя.
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 🔥 очистка старого GPT-контекста (теперь не нужен)
    context.user_data.pop("system_prompt", None)
    context.user_data.pop("help_topic", None)

    reply_markup = get_main_keyboard(is_admin_user=is_admin(user.id))

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=reply_markup
    )


# Показывает меню экстренной помощи на дороге.
async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'main_menu'

    await update.message.reply_text(
        "Здравствуйте! Что случилось?",
        reply_markup=get_help_keyboard()
    )


# Выполняет возврат пользователя в предыдущее меню.
async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('previous_state')

    if state == 'help_menu':
        await show_help_menu(update, context)
    elif state == 'services_menu':
        await handle_services(update, context)
    elif state == 'auto_help_submenu':
        await show_auto_help_submenu(update, context)
    else:
        await show_main_menu(update, context)


# =======================
# 🔹 ОБРАБОТКА КНОПОК
# =======================

# Обрабатывает выбор причины обращения в меню помощи.
async def handle_help_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'help_menu'

    choice = update.message.text

    responses = HELP_PROMPTS

    reply = responses.get(choice)

    if not reply:
        return

    add_message(update.effective_user.id, "user", choice)

    await update.message.reply_text(
        reply,
        parse_mode="HTML",
        reply_markup=get_contact_keyboard()
    )


# Показывает список основных услуг компании.
async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'main_menu'

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_services_keyboard()
    )


# Показывает подробное описание выбранной основной услуги.
async def show_service_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает описание основной услуги.
    Тексты берутся из prompts/service_prompts.py
    """

    service = update.message.text

    if service == btn.BTN_BACK:
        await show_main_menu(update, context)
        return

    text = SERVICES_PROMPTS.get(service)

    if not text:
        logger.warning(f"Не найден текст услуги: {service}")
        return

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


# Показывает подменю раздела Авто-помощь.
async def show_auto_help_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'services_menu'

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_auto_help_keyboard()
    )


# Показывает подробное описание выбранной услуги автопомощи.
async def show_auto_help_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает описание услуги из раздела Авто-помощь.
    Тексты берутся из prompts/service_prompts.py
    """

    service = update.message.text

    if service == btn.BTN_BACK:
        await handle_services(update, context)
        return

    text = AUTO_HELP_PROMPTS.get(service)

    if not text:
        logger.warning(f"Не найден текст услуги автопомощи: {service}")
        return

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


# =======================
# 🔹 СЛУЖЕБНОЕ
# =======================

# Показывает Telegram ID пользователя.
async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Ваш ID: {user_id}")



# Обрабатывает отправленный пользователем номер телефона.
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    phone = update.message.contact.phone_number

    from database import save_client_info

    save_client_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=phone
    )

    add_message(user.id, "user", "[CONTACT]")

    await update.message.reply_text(
        "Спасибо! Мы свяжемся с вами.",
        reply_markup=get_main_keyboard()
    )


# =======================
# 🔹 РЕГИСТРАЦИЯ
# =======================

# Возвращает список служебных обработчиков Telegram-бота.
def get_utility_handlers():
    return [
        CommandHandler("id", show_id),
        MessageHandler(filters.CONTACT, handle_contact),
        MessageHandler(filters.Text(btn.BTN_SERVICES), handle_services),
    ]


# Показывает контактную информацию компании.
async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает контакты компании"""

    context.user_data['previous_state'] = 'main_menu'

    reply_markup = get_back_keyboard()

    # 📞 Отправляем контакт
    await update.message.reply_contact(
        phone_number="+74952369990",
        first_name="Professional24",
        last_name="Сервис"
    )

    # 📝 Текст
    text = (
        "📞 Телефон: +7 495 236-99-90\n"
        "🌐 Сайт: https://professional24.ru/\n\n"
        "Работаем круглосуточно 🚗"
    )

    await update.message.reply_text(
        text,
        reply_markup=reply_markup
    )