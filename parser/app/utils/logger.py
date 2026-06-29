"""
logger.py

Централизованный логгер проекта.

Что делает:
1. Логирует все этапы pipeline
2. Используется во всех модулях
3. Позже может быть подключён к Telegram (для live-прогресса)

Важно:
НЕ завязан на Telegram напрямую — это архитектурно правильно.
"""

import logging


def setup_logger():
    logger = logging.getLogger("SmartCrawler")

    logger.setLevel(logging.INFO)

    # формат логов
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# глобальный логгер
logger = setup_logger()
