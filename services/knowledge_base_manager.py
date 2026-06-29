"""
knowledge_base_manager.py

Сервис управления базой знаний.

Отвечает за:

- создание резервной копии;
- активацию новой базы;
- откат на предыдущую версию;
- получение статуса базы.

Архитектура:

parser/output
        ↓
активация
        ↓
data
        ↓
backup

Parser никогда не пишет напрямую в data.

Основной бот никогда не пишет в parser/output.
"""

from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)


# ==========================================================
# Пути основного проекта
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Рабочая база бота
DATA_DIR = PROJECT_ROOT / "data"

# Резервная копия последней рабочей версии
BACKUP_DIR = PROJECT_ROOT / "backup"

# Новая база, собранная parser
PARSER_OUTPUT_DIR = PROJECT_ROOT / "parser" / "output"


# ==========================================================
# Создает резервную копию текущей рабочей базы
# ==========================================================
def create_backup() -> bool:
    """
    Создает резервную копию текущей активной базы.

    Копируются только файлы,
    необходимые для работы RAG.

    Возвращает:
        True  - успех
        False - ошибка
    """

    try:

        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        files_to_backup = [
            "faiss.index",
            "metadata.json"
        ]

        for filename in files_to_backup:

            source = DATA_DIR / filename

            if not source.exists():
                continue

            destination = BACKUP_DIR / filename

            shutil.copy2(
                source,
                destination
            )

        logger.info(
            "✅ Резервная копия базы создана"
        )

        return True

    except Exception as e:

        logger.exception(
            f"Ошибка создания backup: {e}"
        )

        return False
    

# ==========================================================
# Откатывает базу знаний на предыдущую рабочую версию
# ==========================================================
def rollback_to_backup() -> bool:
    """
    Восстанавливает предыдущую рабочую базу знаний
    из резервной копии.

    Используется в двух случаях:

    1. Администратор нажал кнопку:
       "⏪ Откатить предыдущую базу"

    2. Автоматический откат после неудачной
       активации новой базы.

    Алгоритм:

    backup/
        ↓
    data/

    Возвращает:
        True  - успех
        False - ошибка
    """

    try:

        files_to_restore = [
            "faiss.index",
            "metadata.json"
        ]

        # гарантируем существование data/
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        for filename in files_to_restore:

            source = BACKUP_DIR / filename

            if not source.exists():
                raise FileNotFoundError(
                    f"Файл резервной копии не найден: {source}"
                )

            destination = DATA_DIR / filename

            shutil.copy2(
                source,
                destination
            )

        logger.info(
            "✅ Выполнен откат на предыдущую базу"
        )

        return True

    except Exception as e:

        logger.exception(
            f"Ошибка rollback базы: {e}"
        )

        return False

# ==========================================================
# Активирует новую базу знаний
# ==========================================================
def activate_new_base() -> bool:
    """
    Активирует новую базу знаний.

    Алгоритм:

    1. Создаем backup текущей базы.
    2. Копируем новую базу из parser/output.
    3. Возвращаем успех или ошибку.

    На текущем этапе:
    - без reload FAISS;
    - без health check;
    - без rollback.

    Эти механизмы будут добавлены следующим шагом.
    """

    try:

        # ----------------------------------------------
        # 1. Создаем резервную копию
        # ----------------------------------------------
        if not create_backup():
            raise Exception(
                "Не удалось создать резервную копию."
            )

        # ----------------------------------------------
        # 2. Файлы новой базы
        # ----------------------------------------------
        files_to_activate = [
            "faiss.index",
            "metadata.json"
        ]

        # гарантируем существование data/
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # ----------------------------------------------
        # 3. Копируем новую базу
        # ----------------------------------------------
        for filename in files_to_activate:

            source = PARSER_OUTPUT_DIR / filename

            if not source.exists():
                raise FileNotFoundError(
                    f"Не найден файл: {source}"
                )

            destination = DATA_DIR / filename

            shutil.copy2(
                source,
                destination
            )

        logger.info(
            "✅ Новая база активирована"
        )

        return True

    except Exception as e:

        logger.exception(
            f"Ошибка активации базы: {e}"
        )

        return False