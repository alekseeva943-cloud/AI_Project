"""
Работа с клиентами.

Содержит функции для создания, обновления
и получения информации о клиентах.
"""

import logging
import sqlite3

from .config import DB_PATH


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Работа с клиентами.
# ==========================================================

def save_client_info(
    user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    phone: str | None = None,
) -> None:
    """
    Создаёт нового клиента или обновляет
    информацию о существующем.

    Returns:
        None.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            # Проверяем, существует ли клиент.
            cursor.execute(
                "SELECT 1 FROM clients WHERE user_id = ?",
                (user_id,),
            )

            client_exists = cursor.fetchone()

            if client_exists is None:
                # Добавляем нового клиента.
                cursor.execute(
                    """
                    INSERT INTO clients (
                        user_id,
                        username,
                        first_name,
                        last_name,
                        phone
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        first_name,
                        last_name,
                        phone,
                    ),
                )
            else:
                # Обновляем информацию о клиенте.
                cursor.execute(
                    """
                    UPDATE clients
                    SET
                        username = ?,
                        first_name = ?,
                        last_name = ?,
                        phone = ?
                    WHERE user_id = ?
                    """,
                    (
                        username,
                        first_name,
                        last_name,
                        phone,
                        user_id,
                    ),
                )

    except Exception as error:
        logger.error("Ошибка save_client_info: %s", error)


def get_client_info(user_id: int) -> dict | None:
    """
    Возвращает информацию о клиенте.

    Returns:
        dict | None.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    user_id,
                    username,
                    first_name,
                    last_name,
                    phone
                FROM clients
                WHERE user_id = ?
                """,
                (user_id,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "phone": row[4],
            }

    except Exception as error:
        logger.error("Ошибка get_client_info: %s", error)
        return None
    
def get_all_active_user_ids() -> list[int]:
    """
    Возвращает идентификаторы всех клиентов.

    Используется при массовых рассылках.

    Returns:
        list[int].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT user_id
                FROM clients
                """
            )

            return [
                row[0]
                for row in cursor.fetchall()
            ]

    except Exception as error:
        logger.error(
            "Ошибка get_all_active_user_ids: %s",
            error,
        )
        return []


def get_users_with_phone() -> list[int]:
    """
    Возвращает пользователей,
    оставивших номер телефона.

    Returns:
        list[int].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT user_id
                FROM clients
                WHERE phone IS NOT NULL
                  AND phone != ''
                """
            )

            return [
                row[0]
                for row in cursor.fetchall()
            ]

    except Exception as error:
        logger.error(
            "Ошибка get_users_with_phone: %s",
            error,
        )
        return []


def mark_user_blocked(
    user_id: int,
) -> None:
    """
    Помечает пользователя
    как заблокировавшего бота.

    Returns:
        None.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                """
                UPDATE clients
                SET is_blocked = 1
                WHERE user_id = ?
                """,
                (user_id,),
            )

    except Exception as error:
        logger.error(
            "Ошибка mark_user_blocked: %s",
            error,
        )


def get_total_users() -> int:
    """
    Возвращает общее количество клиентов.

    Returns:
        int.
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM clients
                """
            )

            return cursor.fetchone()[0]

    except Exception as error:
        logger.error(
            "Ошибка get_total_users: %s",
            error,
        )
        return 0


def search_clients(
    query: str,
) -> list[dict]:
    """
    Выполняет поиск клиентов
    по основным полям.

    Returns:
        list[dict].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            search_query = f"%{query}%"

            cursor.execute(
                """
                SELECT *
                FROM clients
                WHERE username LIKE ?
                   OR first_name LIKE ?
                   OR last_name LIKE ?
                   OR phone LIKE ?
                """,
                (
                    search_query,
                    search_query,
                    search_query,
                    search_query,
                ),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    except Exception as error:
        logger.error(
            "Ошибка search_clients: %s",
            error,
        )
        return []
    

def get_total_clients_count() -> int:
    """
    Возвращает общее количество клиентов.

    Returns:
        int.
    """

    return get_total_users()


def get_clients_paginated(
    offset: int,
    limit: int,
) -> list[dict]:
    """
    Возвращает страницу клиентов.

    Используется для постраничного просмотра
    списка пользователей.

    Returns:
        list[dict].
    """

    try:
        with sqlite3.connect(DB_PATH) as connection:
            connection.row_factory = sqlite3.Row

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT *
                FROM clients
                ORDER BY joined_at DESC
                LIMIT ? OFFSET ?
                """,
                (
                    limit,
                    offset,
                ),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    except Exception as error:
        logger.error(
            "Ошибка get_clients_paginated: %s",
            error,
        )
        return []