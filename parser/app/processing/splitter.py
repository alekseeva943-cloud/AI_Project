# Модуль разбиения текста
# Функция: split_text
"""
splitter.py

Модуль отвечает за финальную подготовку блоков перед chunking.

Что делает:
1. Очищает текст (финальная чистка)
2. Разбивает длинный текст на предложения
3. Делит длинные куски на части
4. Обрабатывает списки (list → массив элементов)

Важно:
Это последний этап перед токенизацией и chunking.
"""

import re
from app.utils.logger import logger
from app.config.settings import MAX_TEXT_LENGTH


# =========================
# 🧹 Финальная чистка текста
# =========================
def clean_text(text: str) -> str | None:
    """
    Финальная очистка текста.

    ВАЖНО:
    Если встречается [[[...]]] → сразу удаляем блок (возвращаем None)
    """

    # если явно мусор
    if "[[[" in text:
        return None

    # исправляем склейки (более универсально)
    text = re.sub(r'(?<!\s)([А-ЯA-Z])', r' \1', text)

    # убираем лишние слэши
    text = re.sub(r'\\+', '', text)

    # нормализуем пробелы
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# =========================
# ✂️ Разбиение текста
# =========================
def split_text(text: str) -> list:
    """
    Делит текст на предложения и собирает их в куски.

    Логика:
    - делим по предложениям (. ! ?)
    - собираем, пока не превышаем MAX_TEXT_LENGTH
    """

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current = ""

    for sentence in sentences:

        # если помещается → добавляем
        if len(current) + len(sentence) < MAX_TEXT_LENGTH:
            current += " " + sentence
        else:
            chunks.append(current.strip())
            current = sentence

    if current:
        chunks.append(current.strip())

    return chunks


# =========================
# 📋 Обработка списка
# =========================
def process_list(content: str) -> list:
    """
    Делит строку списка на элементы.

    Пример:
    "ремонт, заправка, диагностика"
    → ["ремонт", "заправка", "диагностика"]
    """

    parts = re.split(r'[.;,]', content)

    # убираем мусор
    parts = [p.strip() for p in parts if len(p.strip()) > 5]

    return parts


# =========================
# 🔄 Основная функция
# =========================
def process_blocks(blocks: list) -> list:
    """
    Обрабатывает блоки после block_builder.

    На вход:
    [
        {"type": "text", "content": "..."}
    ]

    На выход:
    список финальных кусочков
    """

    logger.info("✂️ Финальная обработка блоков")

    result = []

    for block in blocks:
        text = clean_text(block["content"])

        if not text:
            continue

        # =========================
        # 📋 LIST
        # =========================
        if block["type"] == "list":
            items = process_list(text)

            result.append({
                "type": "list",
                "title": block["title"],
                "content": items,
                "url": block.get("url"),
                "page_title": block.get("page_title"),
            })

        # =========================
        # 📄 TEXT
        # =========================
        else:
            pieces = split_text(text)

            for piece in pieces:
                result.append({
                    "type": "text",
                    "title": block["title"],
                    "content": piece,
                    "url": block.get("url"),
                    "page_title": block.get("page_title"),
                })

    logger.info(f"✅ После split: {len(result)} элементов")

    return result
