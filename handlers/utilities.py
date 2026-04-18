# utilities.py

import logging

from telegram import ReplyKeyboardRemove, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from config import is_admin, get_main_keyboard
from config.config import CONTEXT_MESSAGE_COUNT

from database import add_message, get_last_messages, DB_PATH

logger = logging.getLogger(__name__)


# =======================
# 🔹 КЛАВИАТУРЫ
# =======================

def get_services_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛞 Шиномонтаж"), KeyboardButton("❄️ Кондиционер")],
        [KeyboardButton("🚗 Хранение"), KeyboardButton("🔧 Авто-помощь")],
        [KeyboardButton("⬅️ Вернуться")]
    ], resize_keyboard=True)


def get_auto_help_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("⛽ Подвоз топлива"),
         KeyboardButton("💡 Запуск двигателя")],
        [KeyboardButton("🔒 Отключение сигнализации"),
         KeyboardButton("💻 Компьютерная диагностика")],
        [KeyboardButton("⬅️ Вернуться")]
    ], resize_keyboard=True)


# =======================
# 🔹 МЕНЮ
# =======================

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 🔥 очистка старого GPT-контекста (теперь не нужен)
    context.user_data.pop("system_prompt", None)
    context.user_data.pop("help_topic", None)

    reply_markup = get_main_keyboard(is_admin_user=is_admin(user.id))

    await update.message.reply_text("Выберите услугу:", reply_markup=reply_markup)


async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'main_menu'

    keyboard = [
        [KeyboardButton("🛞 Спустило колесо"), KeyboardButton("⛽ Нет топлива")],
        [KeyboardButton("🚗 Не заводится"), KeyboardButton("❄️ Отогреть")],
        [KeyboardButton("🌬 Кондиционер"), KeyboardButton("⚡ Электрика")],
        [KeyboardButton("🔓 Вскрыть"), KeyboardButton("💻 Диагностика")],
        [KeyboardButton("❓ Прочее")],
        [KeyboardButton("⬅️ Вернуться")]
    ]

    await update.message.reply_text(
        "Здравствуйте! Что случилось?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


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

async def handle_help_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'help_menu'

    choice = update.message.text

    responses = {
        "🛞 Спустило колесо": "Мы быстро приедем и решим проблему с колесом.",
        "⛽ Нет топлива": "Доставим топливо прямо к вам.",
        "🚗 Не заводится": "Поможем запустить автомобиль.",
        "❄️ Отогреть": "Аккуратно прогреем авто.",
        "🌬 Кондиционер": "Проверим и починим кондиционер.",
        "⚡ Электрика": "Разберёмся с электрикой.",
        "🔓 Вскрыть": "Откроем авто без повреждений.",
        "💻 Диагностика": "Проведём диагностику.",
        "❓ Прочее": "Опишите ситуацию."
    }

    reply = responses.get(choice)

    if not reply:
        return

    add_message(update.effective_user.id, "user", choice)

    await update.message.reply_text(
        reply,
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📞 Оставить телефон", request_contact=True)],
            [KeyboardButton("📍 Отправить локацию", request_location=True)],
            [KeyboardButton("⬅️ Вернуться")]
        ], resize_keyboard=True)
    )


async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'main_menu'

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_services_keyboard()
    )


async def show_service_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.message.text

    descriptions = {
        "🛞 Шиномонтаж": "Полный комплекс шиномонтажа.",
        "❄️ Кондиционер": "Обслуживание кондиционеров.",
        "🚗 Хранение": "Безопасное хранение авто.",
        "🔧 Авто-помощь": "Помощь на дороге."
    }

    if service == "⬅️ Вернуться":
        await show_main_menu(update, context)
        return

    text = descriptions.get(service)
    if not text:
        return

    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True)
    )


async def show_auto_help_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['previous_state'] = 'services_menu'

    await update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_auto_help_keyboard()
    )


async def show_auto_help_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    service = update.message.text

    descriptions = {
        "⛽ Подвоз топлива": "Доставим топливо.",
        "💡 Запуск двигателя": "Запустим авто.",
        "🔒 Отключение сигнализации": "Отключим сигнализацию.",
        "💻 Компьютерная диагностика": "Сделаем диагностику."
    }

    if service == "⬅️ Вернуться":
        await handle_services(update, context)
        return

    text = descriptions.get(service)
    if not text:
        return

    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True)
    )


# =======================
# 🔹 СЛУЖЕБНОЕ
# =======================

async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Ваш ID: {user_id}")


async def handle_real_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    location = update.message.location

    if not location:
        return

    lat, lon = location.latitude, location.longitude

    add_message(user.id, "user", f"LOCATION {lat},{lon}")

    from handlers.gpt_chat import notify_manager

    await notify_manager(
        context,
        f"📍 {user.id} отправил локацию: {lat},{lon}"
    )

    await update.message.reply_text(
        "Геолокация получена",
        reply_markup=get_main_keyboard()
    )


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

def get_utility_handlers():
    return [
        CommandHandler("id", show_id),
        MessageHandler(filters.LOCATION, handle_real_location),
        MessageHandler(filters.CONTACT, handle_contact),
        MessageHandler(filters.Text("🛠 Наши услуги"), handle_services),
    ]


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает контакты компании"""

    context.user_data['previous_state'] = 'main_menu'

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]],
        resize_keyboard=True
    )

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

    await update.message.reply_text(text, reply_markup=reply_markup)
