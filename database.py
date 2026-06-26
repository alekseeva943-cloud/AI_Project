# database.py

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

# =======================
# 🔹 ПУТЬ
# =======================

DB_PATH = Path(__file__).parent / "data" / "dialogs.db"
DB_PATH.parent.mkdir(exist_ok=True)


# =======================
# 🔹 INIT
# =======================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # --- CLIENTS ---
        cur.execute("""
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

        # --- MESSAGES ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # --- ADMINS ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()


# =======================
# 🔹 CLIENT
# =======================

def save_client_info(user_id, username, first_name, last_name, phone=None):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            cur.execute("SELECT 1 FROM clients WHERE user_id = ?", (user_id,))
            exists = cur.fetchone()

            if not exists:
                cur.execute("""
                    INSERT INTO clients (user_id, username, first_name, last_name, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, phone))
            else:
                cur.execute("""
                    UPDATE clients
                    SET username=?, first_name=?, last_name=?, phone=?
                    WHERE user_id=?
                """, (username, first_name, last_name, phone, user_id))

    except Exception as e:
        logger.error(f"Ошибка save_client_info: {e}")


def get_client_info(user_id: int) -> dict | None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT user_id, username, first_name, last_name, phone
                FROM clients
                WHERE user_id = ?
            """, (user_id,))

            row = cur.fetchone()

            if not row:
                return None

            return {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "phone": row[4]
            }

    except Exception as e:
        logger.error(f"Ошибка get_client_info: {e}")
        return None


# =======================
# 🔹 MESSAGES (🔥 ВАЖНО)
# =======================

def add_message(user_id: int, role: str, content: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
    except Exception as e:
        logger.error(f"Ошибка add_message: {e}")


def get_last_messages(user_id: int, db_path, limit: int = 10) -> List[Dict]:
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT role, content
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            rows = cur.fetchall()
            rows = list(reversed(rows))

            return [{"role": r["role"], "content": r["content"]} for r in rows]

    except Exception as e:
        logger.error(f"Ошибка get_last_messages: {e}")
        return []


# =======================
# 🔹 ADMINS
# =======================

def add_admin(db_path: str, user_id: int, username, first_name, last_name, added_by):
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO admins (user_id, username, first_name, last_name, added_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, added_by))


def remove_admin(db_path: str, user_id: int):
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))


def get_all_admins(db_path: str):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins ORDER BY added_at DESC")
        return [dict(row) for row in cur.fetchall()]


def is_admin(db_path: str, user_id: int) -> bool:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cur.fetchone() is not None


# =======================
# 🔹 ADMIN EXTRA
# =======================

def get_last_n_messages(user_id: int, n: int = 20):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT role, content, timestamp
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, n))

            rows = cur.fetchall()
            return [dict(r) for r in reversed(rows)]

    except Exception as e:
        logger.error(f"Ошибка get_last_n_messages: {e}")
        return []


def get_all_active_user_ids():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM clients")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка get_all_active_user_ids: {e}")
        return []


def get_users_with_phone():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id FROM clients
                WHERE phone IS NOT NULL AND phone != ''
            """)
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка get_users_with_phone: {e}")
        return []


def mark_user_blocked(user_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE clients SET is_blocked = 1 WHERE user_id = ?",
                (user_id,)
            )
    except Exception as e:
        logger.error(f"Ошибка mark_user_blocked: {e}")


# =======================
# 🔹 ДОП ФУНКЦИИ ДЛЯ ADMIN (чтобы не падало)
# =======================

def get_total_users():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM clients")
            return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка get_total_users: {e}")
        return 0


def search_clients(query: str):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            query = f"%{query}%"

            cur.execute("""
    SELECT * FROM clients
    WHERE username LIKE ?
       OR first_name LIKE ?
       OR last_name LIKE ?
       OR phone LIKE ?
""", (query, query, query, query))

            return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Ошибка search_clients: {e}")
        return []


def get_top_requests(days: int = 7):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT content, COUNT(*) as count
                FROM messages
                WHERE role='user'
                GROUP BY content
                ORDER BY count DESC
                LIMIT 10
            """)

            return cur.fetchall()

    except Exception as e:
        logger.error(f"Ошибка get_top_requests: {e}")
        return []


def get_detailed_stats(days=None):
    """
    Возвращает статистику для админки.

    days:
        None -> общая статистика
        1    -> сегодня
        7    -> неделя
        30   -> месяц
        365  -> год
    """

    import sqlite3
    from datetime import datetime, timedelta

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats = {}

    # =========================
    # Всего пользователей
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM clients
    """)
    stats["total_users"] = cursor.fetchone()[0]

    # =========================
    # Пользователей с телефоном
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM clients
        WHERE phone IS NOT NULL
        AND phone != ''
    """)
    stats["with_phone"] = cursor.fetchone()[0]

    # Конверсия в телефон
    if stats["total_users"] > 0:
        stats["phone_conversion"] = round(
            stats["with_phone"] / stats["total_users"] * 100,
            1
        )
    else:
        stats["phone_conversion"] = 0

    # =========================
    # Заблокировали бота
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM clients
        WHERE is_blocked = 1
    """)
    stats["blocked_count"] = cursor.fetchone()[0]

    # =========================
    # Активные чаты за 24 часа
    # =========================
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM messages
        WHERE timestamp >= datetime('now', '-1 day')
    """)
    stats["active_chats_24h"] = cursor.fetchone()[0]

    # =========================
    # Новые пользователи сегодня
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM clients
        WHERE joined_at >= datetime('now', '-1 day')
    """)
    stats["new_today"] = cursor.fetchone()[0]

    # =========================
    # Новые пользователи за неделю
    # =========================
    cursor.execute("""
        SELECT COUNT(*)
        FROM clients
        WHERE joined_at >= datetime('now', '-7 day')
    """)
    stats["new_last_7_days"] = cursor.fetchone()[0]

    # =========================
    # Активные за 30 дней
    # =========================
    cursor.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM messages
        WHERE timestamp >= datetime('now', '-30 day')
    """)
    stats["active_last_30_days"] = cursor.fetchone()[0]

    conn.close()

    return stats


def get_total_clients_count():
    return get_total_users()


def get_paginated_messages(user_id: int, offset: int, limit: int = 20):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT role, content, timestamp
                FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))

            rows = cur.fetchall()
            return [dict(row) for row in reversed(rows)]

    except Exception as e:
        logger.error(f"Ошибка get_paginated_messages: {e}")
        return []


def get_total_messages_count(user_id: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM messages WHERE user_id = ?
            """, (user_id,))

            return cur.fetchone()[0]

    except Exception as e:
        logger.error(f"Ошибка get_total_messages_count: {e}")
        return 0


def get_clients_paginated(offset: int, limit: int):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM clients
                ORDER BY joined_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Ошибка get_clients_paginated: {e}")
        return []
# =======================
# 🔹 INIT CALL
# =======================


init_db()
