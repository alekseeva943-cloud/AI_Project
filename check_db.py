# check_db.py

import sqlite3
from database import DB_PATH


def check_clients():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients")
        rows = cur.fetchall()

        print(f"Найдено клиентов: {len(rows)}\n")

        for row in rows:
            data = dict(row)
            print("—"*40)
            for key, value in data.items():
                print(f"{key}: {value}")


if __name__ == "__main__":
    check_clients()


# запуск проверки БД python check_db.py
