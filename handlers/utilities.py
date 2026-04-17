# utilities.py

from database import add_message, get_last_messages  # ← добавлен импорт
from telegram import ReplyKeyboardRemove, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from config import is_admin, get_main_keyboard
import logging
from database import get_last_messages, DB_PATH
from config.config import PROMPT_TEMPLATES, SYSTEM_PROMPT
from config.config import CONTEXT_MESSAGE_COUNT
from handlers.menu import main_menu_handler  # Для кнопки "Назад"

logger = logging.getLogger(__name__)


# --- Новая часть: Подменю "Наши услуги" ---

def get_services_keyboard():
    """Возвращает клавиатуру с услугами"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛞 Шиномонтаж"), KeyboardButton("❄️ Кондиционер")],
        [KeyboardButton("🚗 Хранение"), KeyboardButton("🔧 Авто-помощь")],
        [KeyboardButton("⬅️ Вернуться")]
    ], resize_keyboard=True)


async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подменю 'Нужна помощь' с отдельной кнопкой '⬅️ Вернуться'"""
    context.user_data['previous_state'] = 'main_menu'  # ← из главного меню
    keyboard = [
        [KeyboardButton("🛞 Спустило колесо"), KeyboardButton("⛽ Нет топлива")],
        [KeyboardButton("🚗 Не заводится"), KeyboardButton("❄️ Отогреть")],
        [KeyboardButton("🌬 Кондиционер"), KeyboardButton("⚡ Электрика")],
        [KeyboardButton("🔓 Вскрыть"), KeyboardButton("💻 Диагностика")],
        [KeyboardButton("❓ Прочее")],  # Одна кнопка в строке
        [KeyboardButton("⬅️ Вернуться")]  # Отдельная строка для "Назад"
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Здравствуйте! Что случилось?", reply_markup=reply_markup)


async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возвращает пользователя на предыдущий шаг"""
    previous_state = context.user_data.get('previous_state')

    if previous_state == 'main_menu':
        await show_main_menu(update, context)
    elif previous_state == 'help_menu':
        await show_help_menu(update, context)
    elif previous_state == 'services_menu':
        await handle_services(update, context)
    elif previous_state == 'auto_help_submenu':
        await show_auto_help_submenu(update, context)
    elif previous_state == 'settings_menu':
        # Возврат в админ-панель — но без импорта show_admin_panel!
        # Просто отправим клавиатуру напрямую
        from config import get_admin_keyboard
        await update.message.reply_text("🛠 Админ-панель:", reply_markup=get_admin_keyboard())
        context.user_data['previous_state'] = 'admin_panel'
    elif previous_state == 'admin_panel':
        # Возврат в главное меню (или туда, откуда пришли)
        return_to = context.user_data.get('return_to_after_admin', 'main_menu')
        context.user_data['previous_state'] = return_to
        if return_to == 'main_menu':
            await show_main_menu(update, context)
        else:
            await show_main_menu(update, context)  # fallback
    else:
        await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню с учётом прав пользователя и очищает контекст"""
    user = update.effective_user

    # --- Сброс контекста ---
    if 'system_prompt' in context.user_data:
        del context.user_data['system_prompt']
    if 'help_topic' in context.user_data:
        del context.user_data['help_topic']

    if is_admin(user.id):
        reply_markup = get_main_keyboard(is_admin_user=True)
    else:
        reply_markup = get_main_keyboard()

    await update.message.reply_text("Выберите услугу:", reply_markup=reply_markup)


async def handle_help_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора в подменю 'Нужна помощь'. Ответы на нажатие кнопки"""
    context.user_data['previous_state'] = 'help_menu'
    choice = update.message.text
    responses = {
        "🛞 Спустило колесо": "Не волнуйтесь — это частая ситуация.\nМы быстро приедем, разберёмся с колесом: подкачаем, починим или заменим его на запасное. Если нужно, привезём новую покрышку прямо к вам.\nОпишите подробнее свою ситуацию или оставьте номер — мы свяжемся с вами в течение минуты.",
        "⛽ Нет топлива": "Не волнуйтесь — такое случается с каждым.\n\nМы быстро доставим необходимое количество топлива прямо к вашей машине, чтобы вы могли продолжить путь без задержек.\n\nВы можете скинуть местоположение через кнопку в меню или оставить свой номер телефона — мы выручим Вас в любое врем дня и ночи.",
        "🚗 Не заводится": "Не переживайте, мы специализируемся на экстренной помощи на дорогах и знаем, как быстро запустить двигатель даже в сложных ситуациях.\n\nПриедем в течение 30–60 минут и поможем: дадим прикурить, зарядим аккумулятор или устраним неисправность прямо на месте.\n\nОпишите подробности или оставьте номер телефона — выезжаем немедленно.",
        "❄️ Отогреть": "Не переживайте, мы специализируемся на экстренной помощи в зимних условиях и знаем, как завести авто даже после сильных морозов.\n\nПриедем в течение 30–60 минут, прогреем двигатель и систему зажигания — всё сделаем качественно, без повреждений и с гарантией результата.\n\nОпишите ситуацию или оставьте телефон — мы свяжемся с вами сразу.",
        "🌬 Кондиционер": "Мы знаем, как важно комфортное охлаждение в жару.\n\nПриедем в течение 30–60 минут, проведём диагностику системы кондиционирования и решим любую проблему:\n\nзаправим фреон, устраним утечки, отремонтируем трубы или восстановим работу компрессора.\n\nРаботаем быстро, качественно и без лишних хлопот. Опишите ситуацию или оставьте телефон — мы свяжемся с вами немедленно.",
        "⚡ Электрика": "Приедем в течение 30–60 минут, диагностируем и устраним неисправности электрики: проводки, генератора, стартера, отключим сигнализацию — прямо на месте.\n\nРаботаем быстро и надёжно.\nОпишите свою ситуацию или оставьте номер — мы сразу перезвоним Вам.",
        "🔓 Вскрыть": "Приедем в течение 30–60 минут и откроем автомобиль без повреждений — двери, капот или багажник.\n\nСпециалисты работают профессиональными инструментами, быстро и аккуратно. Если сработала сигнализация — отключим её.\n\nОпишите ситуацию или оставьте телефон — мы свяжемся с вами немедленно.",
        "💻 Диагностика": "Приедем в течение 30–60 минут и проведём полную компьютерную диагностику автомобиля.\n\nПроверим все системы — от двигателя до бортовой электроники — и сразу сообщим о результатах. Подходит для профилактики, перед покупкой или при появлении тревожных симптомов.\n\nРаботаем с профессиональным оборудованием — быстро, точно, без лишних слов. Опишите ситуацию или оставьте телефон — мы свяжемся с вами.",
        "❓ Прочее": "🏗 Аренда мини бетононасоса: Компактный бетононасос — идеальное решение для частного строительства, дач или небольших объектов.\n\nЛегко маневрирует и работает даже в труднодоступных местах, куда не подъехать крупной технике. Подходит для заливки фундаментов, полов, опор и других бетонных конструкций.\n\nАрендуйте на необходимое время — без лишних затрат на покупку. Стоимость аренды: 25 000 рублей за смену (8 часов).\n\nОставьте свой номер телефона или уточните детали — мы свяжемся с вами немедленно."
    }

    # --- Маппинг кнопок на ключи промтов ---
    help_topic_mapping = {
        "🛞 Спустило колесо": "flat_tire",
        "⛽ Нет топлива": "fuel_delivery",
        "🚗 Не заводится": "engine_start",
        "❄️ Отогреть": "winter_help",
        "🌬 Кондиционер": "ac",
        "⚡ Электрика": "electrics",
        "🔓 Вскрыть": "unlock",
        "💻 Диагностика": "diagnostics",
        "❓ Прочее": "other_help"
    }

    # Получаем ключ для промпта
    template_key = help_topic_mapping.get(choice)
    logger.info(f"[handle_help_choice] template_key = {template_key}")
    if not template_key:
        logger.warning(f"Неизвестная тема: {choice}")
        await update.message.reply_text("Извините, не могу помочь с этим запросом.")
        return

    # Загружаем системный промпт из JSON
    system_prompt = PROMPT_TEMPLATES.get(template_key, SYSTEM_PROMPT)
    context.user_data['system_prompt'] = system_prompt
    logger.info(
        f"[handle_help_choice] PROMPT_TEMPLATES.keys() = {list(PROMPT_TEMPLATES.keys())}")

    # Логируем после успешного получения template_key и system_prompt
    logger.info(
        f"[handle_help_choice] Используется промт для {template_key}: {system_prompt[:100]}...")

    # Показываем пользователю описание темы
    reply_text = responses.get(
        choice, "Извините, не могу помочь с этим запросом.")

    # Добавляем клавиатуру с кнопками
    reply_markup = ReplyKeyboardMarkup([
        [KeyboardButton("📞 Оставить телефон", request_contact=True)],
        [KeyboardButton("📍 Отправить локацию", request_location=True)],
        [KeyboardButton("⬅️ Вернуться")]
    ], resize_keyboard=True)

    # Сохраняем в историю
    add_message(update.effective_user.id, "user", choice)

    # Отправляем ответ
    await update.message.reply_text(reply_text, reply_markup=reply_markup)


async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню услуг с кнопками"""
    context.user_data['previous_state'] = 'main_menu'
    try:
        if update.callback_query:
            await update.callback_query.answer()
            chat = update.callback_query.message.chat
        else:
            chat = update.message.chat

        await context.bot.send_message(
            chat_id=chat.id,
            text="Выберите интересующую вас услугу:",
            reply_markup=get_services_keyboard()
        )
        logger.info(
            f"Показано подменю 'Наши услуги' для пользователя {chat.id}")
    except Exception as e:
        logger.error(f"Ошибка в handle_services: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки услуг.")


# --- Новая функция: Показ деталей услуги ---
async def show_service_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает описание выбранной услуги"""
    service = update.message.text

    descriptions = {
        "🛞 Шиномонтаж": "Мы предлагаем полный комплекс услуг по шиномонтажу: установка, балансировка, ремонт проколов и многое другое.",
        "❄️ Кондиционер": "Диагностика и обслуживание автокондиционеров, заправка хладагента, замена фильтров и устранение утечек.",
        "🚗 Хранение": "Безопасное хранение вашего автомобиля на закрытой территории с круглосуточной охраной.",
        "🔧 Авто-помощь": "Авто-помощь на дороге, техническое обслуживание, компьютерная диагностика и прочие услуги."
    }

    if service == "⬅️ Вернуться":
        await update.message.reply_text("Вы вернулись в главное меню", reply_markup=get_main_keyboard())
        return

    description = descriptions.get(service)

    if not description:
        return  # Если это не одна из наших кнопок — выходим

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True)
    await update.message.reply_text(description, reply_markup=reply_markup)


# --- Добавляем подменю "Авто-помощь" 2x2 ---

def get_auto_help_keyboard():
    """Клавиатура для подменю 'Авто-помощь'"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("⛽ Подвоз топлива"),
         KeyboardButton("💡 Запуск двигателя")],
        [KeyboardButton("🔒 Отключение сигнализации"),
         KeyboardButton("💻 Компьютерная диагностика")],
        [KeyboardButton("⬅️ Вернуться")]
    ], resize_keyboard=True)


async def show_auto_help_submenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подменю 'Авто-помощь'"""
    context.user_data['previous_state'] = 'services_menu'  # ← из "Наших услуг"
    try:
        if update.callback_query:
            await update.callback_query.answer()
            chat = update.callback_query.message.chat
        else:
            chat = update.message.chat

        await context.bot.send_message(
            chat_id=chat.id,
            text="Выберите услугу авто-помощи:",
            reply_markup=get_auto_help_keyboard()
        )
        logger.info(
            f"Показано подменю 'Авто-помощь' для пользователя {chat.id}")
    except Exception as e:
        logger.error(f"Ошибка в show_auto_help_submenu: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки авто-помощи.")


# --- Показываем детали по каждой услуге авто-помощи ---
async def show_auto_help_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает описание выбранной услуги авто-помощи"""
    service = update.message.text

    descriptions = {
        "⛽ Подвоз топлива": "Мы доставим топливо прямо к вашему автомобилю в любое время.",
        "💡 Запуск двигателя": "Поможем запустить двигатель при разрядке аккумулятора.",
        "🔒 Отключение сигнализации": "Профессиональное отключение сигнализации в случае её сбоя.",
        "💻 Компьютерная диагностика": "Точная диагностика всех систем автомобиля с использованием современного оборудования."
    }

    if service == "⬅️ Вернуться":
        await handle_services(update, context)
        return

    description = descriptions.get(service)

    if not description:
        return  # Если это не одна из наших кнопок — выходим

    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]], resize_keyboard=True)
    await update.message.reply_text(description, reply_markup=reply_markup)


# --- Остальные функции остаются без изменений ---

async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ID пользователя"""
    try:
        user_id = update.effective_user.id
        status = " (админ)" if is_admin(user_id) else ""
        await update.message.reply_text(
            f"🆔 Ваш ID: `{user_id}`{status}",
            parse_mode="Markdown"
        )
        logger.info(f"Показан ID для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка в show_id: {e}", exc_info=True)


async def handle_real_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка реальной геолокации от клиента"""
    try:
        user = update.effective_user
        location = update.message.location

        if not location:
            await update.message.reply_text("❌ Не удалось получить координаты.")
            return

        lat = location.latitude
        lon = location.longitude

        # Сохраняем локацию как сообщение от пользователя
        location_text = f"📍 Геолокация: {lat}, {lon}"
        add_message(user.id, "user", location_text)

        # Импорты
        from config.config import CONTEXT_MESSAGE_COUNT, get_main_keyboard
        from database import get_last_messages, DB_PATH  # ← DB_PATH отсюда
        from handlers.gpt_chat import notify_manager

        # Получаем контекст с указанием db_path
        db_history = get_last_messages(
            user.id, db_path=DB_PATH, limit=CONTEXT_MESSAGE_COUNT)

        context_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in db_history]
        ) if db_history else "Нет истории"

        username = f"@{user.username}" if user.username else "без логина"
        admin_message = (
            f"📍 Клиент отправил геолокацию ({username}, ID: {user.id})\n"
            f"Координаты: {lat}, {lon}\n"
            f"🔗 Открыть в картах: https://yandex.ru/maps/?ll={lon}%2C{lat}&z=16\n"
            f"📄 Контекст ({len(db_history)} сообщений):\n{context_text}\n"
            f"🔗 tg://user?id={user.id}"
        )

        await notify_manager(update, context, admin_message)

        reply_markup = get_main_keyboard()
        await update.message.reply_text(
            "✅ Ваша геолокация получена. Менеджер скоро свяжется с вами!",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Ошибка обработки локации: {e}", exc_info=True)
        await update.message.reply_text("❌ Не удалось обработать геолокацию.")


def get_utility_handlers():
    """Регистрация обработчиков"""
    return [
        CommandHandler("id", show_id),
        MessageHandler(filters.LOCATION, handle_real_location),
        MessageHandler(filters.Text("🛠 Наши услуги"), handle_services),
        MessageHandler(filters.CONTACT, handle_contact),

        # Обработчики для услуг
        MessageHandler(
            filters.Text([
                "🛞 Шиномонтаж",
                "❄️ Кондиционер",
                "🚗 Хранение",
                "🔧 Авто-помощь",
                "⬅️ Вернуться"
            ]),
            show_service_details
        ),

        # Обработчики для авто-помощи
        MessageHandler(
            filters.Text([
                "⛽ Подвоз топлива",
                "💡 Запуск двигателя",
                "🔒 Отключение сигнализации",
                "💻 Компьютерная диагностика"
            ]),
            show_auto_help_details
        ),

        # Переход в подменю "Авто-помощь"
        MessageHandler(
            filters.Text("🔧 Авто-помощь"),
            show_auto_help_submenu
        ),
    ]


async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о контактах компании + отправляет контакт"""
    context.user_data['previous_state'] = 'main_menu'
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("⬅️ Вернуться")]],
        resize_keyboard=True
    )

    # 1. Отправляем контакт
    await update.message.reply_contact(
        phone_number="+74952369990",
        first_name="Professional24",
        last_name="Сервис"
    )

    # 2. Текст с информацией
    contacts_info_text = (
        "\n📞 Телефон: +74952369990 (круглосуточно)"
        "\n📧 E-mail: [2369990@mail.ru](mailto:2369990@mail.ru)"
        "\n🌐 Сайт: https://professional24.ru/"
        "\n\n📍 Наши адреса:"
        "\n• г. Москва, ул. Боженко, д. 10, к. 2 (ЗАО)"
        "\n• г. Москва, ул. Анны Ахматовой, д. 22 (м. Рассказовка)"
        "\n• г. Москва, ул. 50 лет Октября, д. 12, с. 8 (р-н Солнцево)"
        "\n• г. Москва, Кутузовский проспект, д. 12 (ЗАО)"
        "\n• г. Москва, Ленинский проспект, д. 168, с. 2 (пересечение со МКАД)"
        "\n• г. Москва, Ленинградское шоссе, д. 8, к. 2 (САО)"
        "\n• г. Москва, Каширское шоссе, д. 148А (ЮАО)"
        "\n• г. Москва, Профсоюзная улица, д. 99 (ЮЗАО)"
        "\n• г. Москва, Мичуринский проспект, д. 31 (ЗАО), к. 1"
    )

    # 2. Отправляем текст с информацией
    await update.message.reply_text(contacts_info_text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка отправленного контакта"""
    user = update.effective_user
    contact = update.message.contact
    phone = contact.phone_number

    from database import save_client_info
    save_client_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=phone
    )

    # Логируем как спец-событие
    add_message(user.id, 'user', '[CONTACT_SHARED]')

    await update.message.reply_text(
        "📞 Спасибо! Мы свяжемся с вами в ближайшее время.",
        reply_markup=get_main_keyboard()
    )
