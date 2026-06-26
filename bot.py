# bot.py

import logging
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# handlers
from handlers.start import start, handle_contact
from handlers.admin import get_admin_handlers, show_admin_panel, show_settings_menu
from handlers.admin_management import show_admins_menu
from handlers.gpt_chat import handle_gpt_query, process_admin_queue

# utilities (всё, что не GPT)
from handlers.utilities import (
    go_back,
    handle_help_choice,
    handle_services,
    handle_real_location,
    show_contacts,
    show_help_menu,
    show_auto_help_submenu,
    show_auto_help_details,
    show_service_details      # ← ДОБАВИЛИ
)

# config
from config import TELEGRAM_TOKEN, SUPERADMIN_ID

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Отключаем лишние логи
for lib in ["httpx", "httpcore", "openai", "telegram", "asyncio"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# --- Инициализация бота ---
async def post_init(application):
    from database import add_admin, DB_PATH
    from config import SUPERADMIN_ID
    import logging

    logger = logging.getLogger(__name__)

    # Гарантируем, что SUPERADMIN всегда в списке
    add_admin(
        db_path=DB_PATH,
        user_id=SUPERADMIN_ID,
        username="Al_leks",
        first_name="Александр",
        last_name=None,
        added_by=SUPERADMIN_ID
    )

    logger.info(f"Бот запущен. Главный админ: {SUPERADMIN_ID}")
    await process_admin_queue(application)


def setup_handlers(app: Application):
    """Регистрация обработчиков событий"""

    # === 0. DEBUG: ловим ВСЁ текстовое ===
    async def debug_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(
            f"[FALLBACK] Получено сообщение: '{update.message.text}' "
            f"от {update.effective_user.id}"
        )

    app.add_handler(
        MessageHandler(
            filters.TEXT,
            debug_all_text
        ),
        group=-1
    )

    # =====================================================
    # 1. БАЗОВЫЕ КОМАНДЫ И СООБЩЕНИЯ
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text("⬅️ Вернуться"),
            go_back
        )
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.CONTACT,
            handle_contact
        )
    )

    app.add_handler(
        MessageHandler(
            filters.LOCATION,
            handle_real_location
        )
    )

    # =====================================================
    # 2. КНОПКИ ВЕРХНЕГО УРОВНЯ
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text("🆘 Нужна помощь"),
            show_help_menu
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Text("🛠 Наши услуги"),
            handle_services
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Text("📱 Наши контакты"),
            show_contacts
        )
    )

    # =====================================================
    # 3. ОСНОВНЫЕ УСЛУГИ
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text([
                "🛞 Шиномонтаж",
                "❄️ Кондиционер",
                "🚗 Хранение"
            ]),
            show_service_details
        )
    )

    # =====================================================
    # 4. ПОДМЕНЮ АВТО-ПОМОЩИ
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text("🔧 Авто-помощь"),
            show_auto_help_submenu
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Text([
                "⛽ Подвоз топлива",
                "💡 Запуск двигателя",
                "🔒 Отключение сигнализации",
                "💻 Компьютерная диагностика"
            ]),
            show_auto_help_details
        )
    )

    # =====================================================
    # 5. КНОПКИ РАЗДЕЛА "НУЖНА ПОМОЩЬ"
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text([
                "🛞 Спустило колесо",
                "⛽ Нет топлива",
                "🚗 Не заводится",
                "❄️ Отогреть",
                "🌬 Кондиционер",
                "⚡ Электрика",
                "🔓 Вскрыть",
                "💻 Диагностика",
                "❓ Прочее",
                "🔙 Назад"
            ]),
            handle_help_choice
        )
    )

    # =====================================================
    # 6. АДМИНКА
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.Text("🛠 Админка"),
            show_admin_panel
        )
    )

    # =====================================================
    # 7. АДМИНСКИЕ ОБРАБОТЧИКИ
    # =====================================================

    for handler in get_admin_handlers():
        app.add_handler(handler)

    # =====================================================
    # 8. ВСЕ ОСТАЛЬНЫЕ ТЕКСТЫ → GPT
    # =====================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_gpt_query
        )
    )


# --- Запуск бота ---
def main():
    try:
        app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .post_init(post_init)
            .build()
        )

        setup_handlers(app)

        logger.info("Бот начал работу")

        # Запуск polling
        app.run_polling()

    except Exception as e:
        logger.critical(f"Фатальная ошибка: {type(e).__name__}")
        raise


if __name__ == "__main__":
    main()
