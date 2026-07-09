"""
database/statistics.py

Статистика базы данных.

Содержит функции для формирования
статистики и аналитики для админ-панели.
"""

import logging
import sqlite3

from .config import DB_PATH
from .config import HELP_REQUEST_BUTTONS


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Топ обращений.
# ==========================================================

def get_top_requests(
    days: int = 7,
) -> list[tuple[str, int]]:
    """
    Возвращает самые популярные обращения
    пользователей за выбранный период.

    Args:
        days: Количество дней для выборки.

    Returns:
        Список кортежей формата (текст_обращения, количество).
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            # Формируем количество плейсхолдеров
            # для оператора IN (...).
            placeholders = ",".join(
                ["?"] * len(HELP_REQUEST_BUTTONS)
            )

            query = f"""
                SELECT
                    content,
                    COUNT(*) AS count
                FROM messages
                WHERE role = 'user'
                  AND content IN ({placeholders})
                  AND timestamp >= datetime('now', ?)
                GROUP BY content
                ORDER BY count DESC
                LIMIT 10
            """

            # Передаём список кнопок
            # и выбранный период.
            parameters = HELP_REQUEST_BUTTONS + [
                f"-{days} days"
            ]

            cursor.execute(
                query,
                parameters,
            )

            return cursor.fetchall()

    except Exception as error:
        logger.error(
            "Ошибка get_top_requests: %s",
            error,
        )
        return []


# ==========================================================
# Сводная статистика.
# ==========================================================

def get_detailed_stats(
    days: int = 30,
) -> dict:
    """
    Возвращает сводную статистику
    для административной панели.

    Абсолютные значения (всего пользователей, всего с телефоном) 
    считаются за все время. Периодические значения (новые, активные) 
    динамически фильтруются по переданному аргументу days.

    Args:
        days: Количество дней для расчета новых и активных пользователей.

    Returns:
        Словарь со статистическими данными.
    """

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        stats = {}

        # ==========================================
        # Абсолютные значения (за все время)
        # ==========================================

        # Общее количество пользователей.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM clients
            """
        )
        stats["total_users"] = cursor.fetchone()[0]

        # Пользователи с номером телефона.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE phone IS NOT NULL
              AND phone != ''
            """
        )
        stats["with_phone"] = cursor.fetchone()[0]

        # Конверсия в оставленный номер телефона.
        if stats["total_users"] > 0:
            stats["phone_conversion"] = round(
                stats["with_phone"] /
                stats["total_users"] * 100,
                1,
            )
        else:
            stats["phone_conversion"] = 0

        # Пользователи, заблокировавшие бота.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE is_blocked = 1
            """
        )
        stats["blocked_count"] = cursor.fetchone()[0]

        # ==========================================
        # Динамические значения (по периоду)
        # ==========================================

        # Активные пользователи за переданный период.
        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM messages
            WHERE timestamp >= datetime('now', ?)
            """,
            (f"-{days} days",)
        )
        stats["active_last_30_days"] = cursor.fetchone()[0]

        # Новые пользователи за переданный период.
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE joined_at >= datetime('now', ?)
            """,
            (f"-{days} days",)
        )
        stats["new_today"] = cursor.fetchone()[0]

        # Заполняем оставшиеся поля для совместимости,
        # если они вызываются где-то еще (из старой(show_stats) логики)
        # Считаем за 7 дней
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM clients
            WHERE joined_at >= datetime('now', '-7 days')
            """
        )
        stats["new_last_7_days"] = cursor.fetchone()[0]

        # Активные за 24 часа (хардкод, так как это стандартный метрик)
        cursor.execute(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM messages
            WHERE timestamp >= datetime('now', '-1 day')
            """
        )
        stats["active_chats_24h"] = cursor.fetchone()[0]

        return stats