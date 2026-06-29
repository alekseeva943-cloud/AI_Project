# Модуль сборки блоков из текста
# Функция: build_blocks
"""
block_builder.py

Модуль отвечает за преобразование очищенного контента в логические блоки.

Что делает:
1. Группирует текст по заголовкам
2. Собирает обычный текст в единые блоки
3. Обрабатывает списки (li)
4. Определяет "скрытые списки" (несколько коротких p подряд)
5. Формирует итоговую структуру

Важно:
Это ключевой этап перед chunking.
"""

from app.utils.logger import logger


# =========================
# 🔍 Эвристика "похоже на услугу"
# =========================
def is_service_like(text: str) -> bool:
    """
    Определяет, похож ли текст на элемент списка.

    Логика:
    - короткий текст
    - нет точки в конце

    Используется для поиска "скрытых списков"
    """

    if len(text) < 120 and not text.endswith("."):
        return True

    return False


# =========================
# 🧱 Построение блоков
# =========================
def build_blocks(content: list) -> list:
    """
    Превращает список элементов (p, li, h1...) в логические блоки.

    На вход:
    [
        {"type": "p", "text": "..."},
        {"type": "h2", "text": "..."}
    ]

    На выход:
    [
        {
            "type": "text",
            "title": "...",
            "content": "..."
        }
    ]
    """

    logger.info("🧱 Построение логических блоков")

    blocks = []

    current_title = None  # текущий заголовок

    buffer_text = []  # накопление текста
    buffer_list = []  # накопление списка

    # =========================
    # 📦 Сброс текстового буфера
    # =========================

    def flush_text():
        nonlocal buffer_text

        if buffer_text:
            blocks.append({
                "type": "text",
                "title": current_title,
                "content": " ".join(buffer_text)
            })
            buffer_text = []

    # =========================
    # 📦 Сброс списка
    # =========================

    def flush_list():
        nonlocal buffer_list

        if buffer_list:
            blocks.append({
                "type": "list",
                "title": current_title,
                "content": ", ".join(buffer_list)
            })
            buffer_list = []

    i = 0
    length = len(content)

    while i < length:
        item = content[i]

        t = item["type"]
        text = item["text"]

        # =========================
        # 🏷 Заголовок
        # =========================
        if t in ["h1", "h2", "h3"]:
            flush_text()
            flush_list()

            current_title = text
            i += 1
            continue

        # =========================
        # 📋 Явный список (li)
        # =========================
        if t == "li":
            flush_text()

            buffer_list.append(text)
            i += 1
            continue

        # =========================
        # 🔍 Скрытый список (несколько коротких p подряд)
        # =========================
        if t == "p" and is_service_like(text):
            flush_text()

            temp_list = [text]
            j = i + 1

            # идём вперёд и ищем похожие элементы
            while j < length:
                next_item = content[j]

                if (
                    next_item["type"] == "p"
                    and is_service_like(next_item["text"])
                ):
                    temp_list.append(next_item["text"])
                    j += 1
                else:
                    break

            # если нашли достаточно элементов → это список
            if len(temp_list) >= 3:
                blocks.append({
                    "type": "list",
                    "title": current_title,
                    "content": ", ".join(temp_list)
                })

                i = j
                continue
            else:
                buffer_text.append(text)
                i += 1
                continue

        # =========================
        # 📄 Обычный текст
        # =========================
        flush_list()

        buffer_text.append(text)
        i += 1

    # финальный сброс
    flush_text()
    flush_list()

    logger.info(f"✅ Построено блоков: {len(blocks)}")

    return blocks
