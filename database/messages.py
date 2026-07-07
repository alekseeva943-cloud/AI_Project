"""
Работа с сообщениями.

Содержит функции для сохранения истории
диалога и получения контекста пользователя.
"""

import logging
import sqlite3
from typing import Dict, List

from .config import DB_PATH


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Работа с сообщениями.
# ==========================================================

def add_message(
    user_id: int,
    role: str,
    content: str,
) -> None:
    """
    Сохраняет сообщение пользователя
    или ассистента в базе данных.

    Returns:
        None.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    user_id,
                    role,
                    content
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    role,
                    content,
                ),
            )

    except Exception as error:
        logger.error("Ошибка add_message: %s", error)


def get_last_messages(
    user_id: int,
    db_path,
    limit: int = 10,
) -> List[Dict]:
    """
    Возвращает последние сообщения пользователя.

    Используется для формирования
    контекста GPT.

    Returns:
        List[Dict].
    """

    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    role,
                    content
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (
                    user_id,
                    limit,
                ),
            )

            rows = cursor.fetchall()

            return [
                {
                    "role": row["role"],
                    "content": row["content"],
                }
                for row in reversed(rows)
            ]

    except Exception as error:
        logger.error("Ошибка get_last_messages: %s", error)
        return []
    
# ==========================================================
# Получение истории сообщений.
# ==========================================================

def get_last_n_messages(
    user_id: int,
    limit: int = 20,
) -> list[dict]:
    """
    Возвращает последние сообщения пользователя
    вместе со временем отправки.

    Используется для просмотра истории
    переписки в административной панели.

    Returns:
        list[dict].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    role,
                    content,
                    timestamp
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (
                    user_id,
                    limit,
                ),
            )

            rows = cursor.fetchall()

            return [
                dict(row)
                for row in reversed(rows)
            ]

    except Exception as error:
        logger.error(
            "Ошибка get_last_n_messages: %s",
            error,
        )
        return []
    

def get_paginated_messages(
    user_id: int,
    offset: int,
    limit: int = 20,
) -> list[dict]:
    """
    Возвращает страницу сообщений пользователя.

    Используется для постраничного просмотра
    истории переписки.

    Returns:
        list[dict].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    role,
                    content,
                    timestamp
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (
                    user_id,
                    limit,
                    offset,
                ),
            )

            rows = cursor.fetchall()

            return [
                dict(row)
                for row in reversed(rows)
            ]

    except Exception as error:
        logger.error(
            "Ошибка get_paginated_messages: %s",
            error,
        )
        return []


def get_total_messages_count(
    user_id: int,
) -> int:
    """
    Возвращает общее количество сообщений
    пользователя.

    Returns:
        int.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM messages
                WHERE user_id = ?
                """,
                (user_id,),
            )

            return cursor.fetchone()[0]

    except Exception as error:
        logger.error(
            "Ошибка get_total_messages_count: %s",
            error,
        )
        return 0