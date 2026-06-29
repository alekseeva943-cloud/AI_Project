# Главный скрипт запуска приложения
"""
main.py

Точка входа в приложение.

Что делает:
1. Загружает токен
2. Создаёт Telegram приложение
3. Подключает обработчики
4. Запускает бота
"""

import os
from dotenv import load_dotenv

from telegram.ext import Application, MessageHandler, filters

from app.bot.handlers import start, handle_text

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def main():
    app = Application.builder().token(TOKEN).build()

    # команды
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))

    # /start
    app.add_handler(MessageHandler(filters.COMMAND, start))

    print("🚀 Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
