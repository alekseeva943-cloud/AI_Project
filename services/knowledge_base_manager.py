# services/knowledge_base_manager.py

"""
Управление базой знаний.

Назначение:
- создание резервной копии базы знаний;
- активация новой базы знаний;
- откат на предыдущую версию;
- получение информации о состоянии базы знаний.

Архитектура:

parser/output
        ↓
активация
        ↓
data
        ↓
backup

Parser никогда не изменяет рабочую базу напрямую.
Основной бот никогда не работает с parser/output.
"""

import json
import logging
import shutil
from pathlib import Path


# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)


# ==========================================================
# Пути проекта.
# ==========================================================

# Корневая директория проекта.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Каталог активной базы знаний.
DATA_DIR = PROJECT_ROOT / "data"

# Каталог резервных копий.
BACKUP_DIR = PROJECT_ROOT / "backup"

# Каталог новой базы, собранной парсером.
PARSER_OUTPUT_DIR = PROJECT_ROOT / "parser" / "output"


# ==========================================================
# Константы модуля.
# ==========================================================

# Файлы, входящие в состав базы знаний.
KNOWLEDGE_BASE_FILES = [
    "faiss.index",
    "metadata.json",
    "build_stats.json",
    "chunks_final.json",
]


# ==========================================================
# Вспомогательные функции.
# ==========================================================

def _load_json(file_path: Path) -> dict | None:
    """
    Загружает JSON-файл.

    Returns:
        dict | None.
    """

    if not file_path.exists():
        return None

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ==========================================================
# Работа с резервными копиями.
# ==========================================================

def create_backup() -> bool:
    """
    Создаёт резервную копию
    текущей рабочей базы знаний.

    Returns:
        bool.
    """

    try:
        # Гарантируем существование каталога backup.
        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Копируем все файлы базы знаний.
        for filename in KNOWLEDGE_BASE_FILES:

            source = DATA_DIR / filename

            if not source.exists():
                continue

            destination = BACKUP_DIR / filename

            shutil.copy2(
                source,
                destination,
            )

        logger.info(
            "✅ Резервная копия базы знаний создана."
        )

        return True

    except Exception:
        logger.exception(
            "Ошибка создания резервной копии."
        )
        return False
    

def rollback_to_backup() -> bool:
    """
    Восстанавливает предыдущую
    рабочую версию базы знаний.

    Используется при ручном или
    автоматическом откате после
    неудачной активации новой базы.

    Returns:
        bool.
    """

    try:
        # Гарантируем существование каталога data.
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Восстанавливаем файлы резервной копии.
        for filename in KNOWLEDGE_BASE_FILES:

            source = BACKUP_DIR / filename

            if not source.exists():

                # Статистика сборки не является
                # обязательным файлом.
                if filename == "build_stats.json":
                    continue

                raise FileNotFoundError(
                    f"Файл резервной копии не найден: {source}"
                )

            destination = DATA_DIR / filename

            shutil.copy2(
                source,
                destination,
            )

        logger.info(
            "✅ Резервная копия успешно восстановлена."
        )

        return True

    except Exception:
        logger.exception(
            "Ошибка восстановления резервной копии."
        )
        return False
    
# ==========================================================
# Активация базы знаний.
# ==========================================================

def activate_new_base() -> bool:
    """
    Активирует новую базу знаний.

    Алгоритм:
    1. Создаёт резервную копию текущей базы.
    2. Копирует новую базу из parser/output.
    3. Делает её активной.

    Returns:
        bool.
    """

    try:
        # Создаём резервную копию текущей базы.
        if not create_backup():
            raise RuntimeError(
                "Не удалось создать резервную копию."
            )

        # Гарантируем существование каталога data.
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Копируем новую базу знаний.
        for filename in KNOWLEDGE_BASE_FILES:

            source = PARSER_OUTPUT_DIR / filename

            if not source.exists():
                raise FileNotFoundError(
                    f"Не найден файл базы знаний: {source}"
                )

            destination = DATA_DIR / filename

            shutil.copy2(
                source,
                destination,
            )

        logger.info(
            "✅ Новая база знаний успешно активирована."
        )

        return True

    except Exception:
        logger.exception(
            "Ошибка активации базы знаний."
        )
        return False


# ==========================================================
# Статус базы знаний.
# ==========================================================

def get_knowledge_base_status() -> dict:
    """
    Возвращает информацию
    о всех версиях базы знаний.

    Returns:
        dict.
    """

    try:
        return {
            "active": _load_json(
                DATA_DIR / "build_stats.json"
            ),
            "new": _load_json(
                PARSER_OUTPUT_DIR / "build_stats.json"
            ),
            "backup": _load_json(
                BACKUP_DIR / "build_stats.json"
            ),
        }

    except Exception:
        logger.exception(
            "Ошибка получения статуса базы знаний."
        )

        return {
            "active": None,
            "new": None,
            "backup": None,
        }