"""
Работа с администраторами.

Содержит функции управления администраторами
и проверки прав доступа.
"""

import logging
import sqlite3


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Работа с администраторами.
# ==========================================================

def add_admin(
    db_path: str,
    user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    added_by: int,
) -> None:
    """
    Добавляет администратора или обновляет
    информацию о существующем.

    Returns:
        None.
    """

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO admins (
                user_id,
                username,
                first_name,
                last_name,
                added_by
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                first_name,
                last_name,
                added_by,
            ),
        )


def remove_admin(
    db_path: str,
    user_id: int,
) -> None:
    """
    Удаляет администратора.

    Returns:
        None.
    """

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "DELETE FROM admins WHERE user_id = ?",
            (user_id,),
        )


def get_all_admins(
    db_path: str,
) -> list[dict]:
    """
    Возвращает список всех администраторов.

    Returns:
        list[dict].
    """

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM admins
            ORDER BY added_at DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def is_admin(
    db_path: str,
    user_id: int,
) -> bool:
    """
    Проверяет наличие пользователя
    в списке администраторов.

    Returns:
        bool.
    """

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM admins
            WHERE user_id = ?
            """,
            (user_id,),
        )

        return cursor.fetchone() is not None