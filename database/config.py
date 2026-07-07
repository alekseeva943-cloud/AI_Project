"""
Конфигурация модуля базы данных.

Содержит общие константы, используемые
всеми файлами пакета database.
"""

from pathlib import Path

from config import buttons as btn


# ==========================================================
# Константы модуля.
# ==========================================================

# Путь к файлу SQLite базы данных.
# Используется всеми модулями пакета database.
DB_PATH = Path(__file__).parent.parent / "data" / "dialogs.db"

# Создаём каталог для базы данных,
# если он ещё не существует.
DB_PATH.parent.mkdir(exist_ok=True)

# Кнопки, считающиеся обращениями клиентов.
# Используются при построении статистики обращений.
HELP_REQUEST_BUTTONS = [
    btn.BTN_FLAT_TIRE,
    btn.BTN_NO_FUEL,
    btn.BTN_NOT_STARTING,
    btn.BTN_WARM_UP,
    btn.BTN_CONDITIONER_PROBLEM,
    btn.BTN_ELECTRIC_PROBLEM,
    btn.BTN_UNLOCK_CAR,
    btn.BTN_DIAGNOSTIC_REQUEST,
    btn.BTN_OTHER_PROBLEM,
]