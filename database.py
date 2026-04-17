# database.py

import sqlite3
from pathlib import Path
from datetime import datetime
import logging

from telegram import User
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

# Путь к БД
DB_PATH = Path(__file__).parent / "data" / "dialogs.db"
DB_PATH.parent.mkdir(exist_ok=True)  # Создаем папку data, если её нет


def init_admins_table(db_path: str):
    """Создаёт таблицу admins, если её нет"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
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
        conn.commit()


def add_admin(db_path: str, user_id: int, username: str | None, first_name: str | None, last_name: str | None, added_by: int):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO admins (user_id, username, first_name, last_name, added_by)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, added_by))
        conn.commit()


def remove_admin(db_path: str, user_id: int):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()


def get_all_admins(db_path: str) -> list[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins ORDER BY added_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def is_admin(db_path: str, user_id: int) -> bool:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None


def init_db():
    """Создает все необходимые таблицы"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Таблица пользователей
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_blocked BOOLEAN DEFAULT 0  -- 0 = активен, 1 = заблокировал
        )
        """)

        # Таблица сообщений (диалоги)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,  -- 'user' или 'assistant'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES clients(user_id)
        )
        """)

        # Существующая таблица dialogs (временно)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS dialogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            message TEXT NOT NULL,
            is_manager BOOLEAN DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()

        # --- Обновление структуры: добавляем недостающие колонки ---
        cur.execute("PRAGMA table_info(clients)")
        columns = [col[1] for col in cur.fetchall()]

        if 'phone' not in columns:
            cur.execute("ALTER TABLE clients ADD COLUMN phone TEXT")
            logger.info(
                "[init_db] Добавлена колонка 'phone' в таблицу clients")

        if 'is_blocked' not in columns:
            cur.execute(
                "ALTER TABLE clients ADD COLUMN is_blocked BOOLEAN DEFAULT 0")
            logger.info(
                "[init_db] Добавлена колонка 'is_blocked' в таблицу clients")


def mark_user_blocked(user_id: int):
    """Помечает пользователя как заблокировавшего бота"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE clients SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            if cur.rowcount > 0:
                logger.info(
                    f"Пользователь {user_id} помечен как заблокировавший")
    except Exception as e:
        logger.error(f"Ошибка пометки blocked для {user_id}: {e}")


def save_client_info(user_id: int, username: str, first_name: str, last_name: str, phone: str = None):
    """Сохраняет или обновляет информацию о пользователе"""
    logger.debug(
        f"Сохраняю клиента {user_id}: username={username}, имя={first_name}, телефон={phone}")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # Проверяем, существует ли запись
            cur.execute("SELECT 1 FROM clients WHERE user_id = ?", (user_id,))
            exists = cur.fetchone()

            if not exists:
                # Вставляем новую запись с телефоном
                cur.execute(
                    """
                    INSERT INTO clients (user_id, username, first_name, last_name, phone)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, username, first_name, last_name, phone)
                )
                logger.info(
                    f"[save_client_info] Новый клиент добавлен: ID={user_id}, телефон={phone}")
            else:
                # Обновляем существующую запись, включая телефон
                cur.execute(
                    """
                    UPDATE clients
                    SET username = ?, first_name = ?, last_name = ?, phone = ?
                    WHERE user_id = ?
                    """,
                    (username, first_name, last_name, phone, user_id)
                )
                logger.info(
                    f"[save_client_info] Клиент обновлён: ID={user_id}, телефон={phone}")

    except Exception as e:
        logger.error(f"Ошибка сохранения клиента: {e}")


def get_all_clients():
    """Возвращает список всех пользователей"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id, username, first_name FROM clients ORDER BY joined_at DESC")
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Ошибка получения клиентов: {e}")
        return []


def add_message(user_id: int, role: str, content: str):
    """Добавляет сообщение в историю диалога"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {e}")


def get_last_messages(user_id: int, db_path: str | Path, limit: int = 7) -> list[dict]:
    """Получает последние N сообщений пользователя"""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT role, content FROM messages
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cur.fetchall()
            rows.reverse()
            return [{"role": row[0], "content": row[1]} for row in rows]
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return []


def get_client_info(user_id: int) -> dict | None:
    """Получает информацию о клиенте по ID"""
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
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'last_name': row[3],
                'phone': row[4]
            }
    except Exception as e:
        logger.error(f"Ошибка получения информации о клиенте: {e}")
        return None


def has_client_phone(user_id: int) -> bool:
    """Проверяет, есть ли у клиента сохранённый номер телефона"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT phone FROM clients WHERE user_id = ?", (user_id,))
            result = cur.fetchone()
            return bool(result and result[0])
    except Exception as e:
        logger.error(f"Ошибка проверки наличия телефона: {e}")
        return False


async def save_dialog(user_id: int, username: str, message: str, is_manager: bool = False):
    """Асинхронное сохранение диалога (временно)"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO dialogs (user_id, username, message, is_manager) VALUES (?, ?, ?, ?)",
                (user_id, username, message, int(is_manager))
            )
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")


def get_total_users() -> int:
    """Возвращает общее количество уникальных пользователей из таблицы clients"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM clients")
            result = cur.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Ошибка получения общего числа пользователей: {e}")
        return 0


def search_clients(query: str) -> List[Dict]:
    """
    Ищет клиентов по:
    - телефону (только цифры, минимум 4)
    - username (без пробелов, минимум 3 символа)
    - имени/фамилии (минимум 5 символов, подстрока, без учёта регистра)
    """
    query = query.strip()
    if not query:
        return []

    results = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Поиск по телефону (только цифры, >=4)
        digits = re.sub(r'\D', '', query)
        if len(digits) >= 4:
            cur.execute("SELECT * FROM clients WHERE phone LIKE ?",
                        (f'%{digits}%',))
            results.extend([dict(row) for row in cur.fetchall()])

        # 2. Поиск по username (если запрос — одно слово без пробелов, >=3)
        if ' ' not in query and len(query) >= 3:
            clean_username = query.lstrip('@')
            cur.execute("SELECT * FROM clients WHERE username LIKE ?",
                        (f'%{clean_username}%',))
            username_results = [dict(row) for row in cur.fetchall()]
            existing_ids = {r['user_id'] for r in results}
            for r in username_results:
                if r['user_id'] not in existing_ids:
                    results.append(r)

        # 3. Поиск по имени/фамилии (>=5 символов)

        if len(query) >= 5:
            query_lower = query.lower()
            cur.execute("SELECT * FROM clients")
            all_clients = [dict(row) for row in cur.fetchall()]
            for client in all_clients:
                first = (client['first_name'] or '').lower()
                last = (client['last_name'] or '').lower()
                if query_lower in first or query_lower in last:
                    if client['user_id'] not in {r['user_id'] for r in results}:
                        results.append(client)

    return results


def get_last_n_messages(user_id: int, n: int = 20) -> List[Dict]:
    """Получает последние N сообщений пользователя из таблицы messages"""
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
            # Разворачиваем, чтобы было в хронологическом порядке
            return [dict(row) for row in reversed(rows)]
    except Exception as e:
        logger.error(f"Ошибка получения сообщений для {user_id}: {e}")
        return []


def get_all_active_user_ids() -> List[int]:
    """Возвращает ID всех клиентов, кто хотя бы раз писал боту"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM clients")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения всех user_id: {e}")
        return []


def get_users_with_phone() -> List[int]:
    """Возвращает ID клиентов, у которых есть телефон"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT user_id FROM clients WHERE phone IS NOT NULL AND phone != ''")
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка получения клиентов с телефоном: {e}")
        return []


def get_detailed_stats() -> dict:
    """Возвращает расширенную статистику по клиентам"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            # Основные счётчики
            cur.execute("SELECT COUNT(*) FROM clients")
            total_users = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM clients WHERE phone IS NOT NULL AND phone != ''")
            with_phone = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM clients WHERE is_blocked = 1")
            blocked_count = cur.fetchone()[0]

            # Активные чаты: писали за последние 24 часа
            cur.execute("""
                SELECT COUNT(DISTINCT user_id) FROM messages 
                WHERE timestamp >= datetime('now', '-1 day')
            """)
            active_chats_24h = cur.fetchone()[0]

            # Новые за периоды
            cur.execute(
                "SELECT COUNT(*) FROM clients WHERE joined_at >= date('now')")
            new_today = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM clients WHERE joined_at >= date('now', '-7 days')")
            new_last_7_days = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(DISTINCT user_id) FROM messages 
                WHERE timestamp >= date('now', '-30 days')
            """)
            active_last_30_days = cur.fetchone()[0]

            return {
                'total_users': total_users,
                'with_phone': with_phone,
                'blocked_count': blocked_count,
                'active_chats_24h': active_chats_24h,
                'new_today': new_today,
                'new_last_7_days': new_last_7_days,
                'active_last_30_days': active_last_30_days,
                'phone_conversion': round(with_phone / total_users * 100, 1) if total_users else 0
            }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {}


def get_top_requests(days: int = 7) -> List[tuple]:
    """
    Возвращает топ-запросов по услугам за N дней.
    Учитываются ТОЛЬКО сообщения, совпадающие с известными кнопками или их ключевыми словами.
    Вежливости и мусор игнорируются.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT datetime('now', ?)", (f'-{days} days',))
            since_date = cur.fetchone()[0]

            cur.execute("""
                SELECT content FROM messages
                WHERE role = 'user' AND timestamp >= ?
            """, (since_date,))
            raw_messages = [row[0] for row in cur.fetchall()]

        if not raw_messages:
            return []

        # Фильтр "мусора"
        def is_noise(msg: str) -> bool:
            msg = msg.strip()
            if len(msg) < 3:
                return True
            lower = msg.lower()
            noise_phrases = {
                "привет", "здравствуйте", "хай", "hello", "hi", "добрый день",
                "ок", "окей", "понял", "ясно", "спасибо", "благодарю", "пасиб",
                "да", "нет", "ладно", "хорошо", "отлично", "ага", "угу",
                "📍 отправить локацию", "📞 отправить контакт",
                "назад", "в меню", "отмена", "стоп", "хватит"
            }
            return lower in noise_phrases

        # Все категории — с точными названиями кнопок из интерфейса
        categories = {
            # Основное меню и контакты
            "🛞 Шиномонтаж": ["🛞 шиномонтаж", "шин", "колес", "балансировк", "покрышк", "диск", "резина", "колёс"],
            "❄️ Кондиционер": ["❄️ кондиционер", "кондиц", "холод", "ac", "фреон", "заправ", "климат", "печка"],
            "📱 Наши контакты": ["📱 наши контакты", "контакт", "связь", "телефон", "адрес"],
            "🛠 Наши услуги": ["🛠 наши услуги"],
            "🆘 Нужна помощь": ["🆘 нужна помощь"],

            # Меню "Нужна помощь"
            "🛞 Спустило колесо": ["спустило колесо", "прокол", "шина спущена", "дырка в шине", "колесо спущено"],
            "⛽ Нет топлива": ["нет топлива", "закончился бензин", "бак пуст", "не едет — нет бензина", "топливо закончилось"],
            "🚗 Не заводится": ["не заводится", "стартер крутит", "тихо", "не запускается", "севший аккум", "зажигание не работает"],
            "❄️ Отогреть": ["отогреть", "замёрз", "машина замерзла", "не открывается", "замок замёрз", "мороз"],
            "🌬 Кондиционер": ["кондиционер не работает", "нет холода", "ac не дует", "не холодит"],
            "⚡ Электрика": ["электрика", "фары", "сигнал", "провод", "короткое", "электрооборудование", "генератор", "стартер"],
            "🔓 Вскрыть": ["вскрыть", "ключи в машине", "закрыл машину", "не могу открыть", "забыл ключи"],
            "💻 Диагностика": ["диагностика", "ошибка", "check", "код ошибки", "компьютер", "сканер"],
            "❓ Прочее": ["❓ прочее", "другое", "не знаю", "что-то ещё", "прочее"]
        }

        counts = {topic: 0 for topic in categories}

        for msg in raw_messages:
            if is_noise(msg):
                continue

            msg_lower = msg.lower()
            matched = False

            for topic, keywords in categories.items():
                # 1. Точное совпадение с названием кнопки (самое важное!)
                if msg == topic:
                    counts[topic] += 1
                    matched = True
                    break
                # 2. Совпадение с альтернативным текстом кнопки (если есть)
                if msg in keywords:
                    counts[topic] += 1
                    matched = True
                    break
                # 3. Поиск по ключевым словам
                for kw in keywords:
                    if kw in msg_lower:
                        counts[topic] += 1
                        matched = True
                        break
                if matched:
                    break

        # Возвращаем только ненулевые, отсортированные по убыванию
        result = [(topic, count)
                  for topic, count in counts.items() if count > 0]
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:10]

    except Exception as e:
        logger.error(f"Ошибка получения топа запросов: {e}")
        return []


def get_clients_paginated(offset: int, limit: int) -> List[dict]:
    """Возвращает клиентов, отсортированных от новых к старым (по joined_at DESC), с пагинацией."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT user_id, username, first_name, last_name, phone, joined_at
                FROM clients
                ORDER BY joined_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка пагинации клиентов: {e}")
        return []


def get_total_clients_count() -> int:
    """Возвращает общее число клиентов."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM clients")
            return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка подсчёта клиентов: {e}")
        return 0


def get_paginated_messages(user_id: int, offset: int, limit: int = 20) -> List[dict]:
    """Получает сообщения пользователя с пагинацией (от новых к старым, но возвращает в хронологическом порядке)."""
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
            # Возвращаем в хронологическом порядке (от старых к новым)
            return [dict(row) for row in reversed(rows)]
    except Exception as e:
        logger.error(f"Ошибка пагинации сообщений для {user_id}: {e}")
        return []


def get_total_messages_count(user_required: int) -> int:
    """Возвращает общее число сообщений у пользователя."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_required,))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка подсчёта сообщений для {user_required}: {e}")
        return 0


# Инициализируем БД при импорте
init_db()
