"""
Инициализация базы данных.

Создаёт структуру SQLite базы данных
при первом запуске проекта.
"""

import sqlite3

from .config import DB_PATH


# ==========================================================
# Инициализация базы данных.
# ==========================================================

def init_db() -> None:
    """
    Создаёт таблицы базы данных,
    если они ещё не существуют.

    Returns:
        None.
    """

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()

        # Создаём таблицу клиентов.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_blocked BOOLEAN DEFAULT 0
        )
        """)

        # Создаём таблицу сообщений.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Создаём таблицу администраторов.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        connection.commit()