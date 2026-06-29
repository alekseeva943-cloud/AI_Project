# =========================
# 🧹 Модуль очистки текста (FINAL PRO VERSION)
# =========================
"""
cleaner.py

ФИНАЛЬНАЯ ВЕРСИЯ (ПОД ПОРТФОЛИО + RAG)

Что делает:
1. Удаляет технический мусор (JSON, скрипты)
2. Исправляет склейки слов
3. Убирает декоративный текст (Б Е С П Л А Т Н О)
4. Удаляет SEO и гео-спам (районы, шоссе и т.д.)
5. Нормализует текст (читаемый вид)
6. Улучшает структуру (мини-абзацы)

Цели:
✔ Красивый TXT файл (читается как статья)
✔ Чистые чанки (лучше embeddings)
✔ Минимум шума в базе

⚠️ ВАЖНО:
Никакой агрессивной магии.
Мы НЕ ломаем смысл текста.
"""

import re
from app.utils.logger import logger


# =========================
# 🧨 Удаление мусора (JSON / скрипты)
# =========================
def remove_garbage(text: str) -> str:
    if not text:
        return ""

    # [[[ ... ]]]
    text = re.sub(r"\[\[\[.*?\]\]\]", " ", text, flags=re.DOTALL)

    # { ... } (JS / JSON)
    text = re.sub(r"\{.*?\}", " ", text, flags=re.DOTALL)

    return text


# =========================
# 🔤 Удаление "Б Е С П Л А Т Н О"
# =========================
def remove_spaced_letters(text: str) -> str:
    """
    Б Е С П Л А Т Н О → БЕСПЛАТНО
    Работает даже при разных пробелах
    """
    return re.sub(
        r"(?:\b[А-ЯЁ]\s+){2,}[А-ЯЁ]\b",
        lambda m: m.group(0).replace(" ", ""),
        text
    )


# =========================
# 🔧 Исправление склеек
# =========================
def fix_spacing(text: str) -> str:
    if not text:
        return ""

    # буква + Заглавная → пробел
    text = re.sub(r"([а-яё])([А-ЯЁ])", r"\1 \2", text)

    # цифра + слово
    text = re.sub(r"(\d)([а-яА-ЯёЁ])", r"\1 \2", text)

    # слово + цифра
    text = re.sub(r"([а-яА-ЯёЁ])(\d)", r"\1 \2", text)

    # точка + слово
    text = re.sub(r"([.,!?])([а-яА-ЯёЁ])", r"\1 \2", text)

    # 📞 нормализация телефона
    text = re.sub(
        r"\+7\s?\(?(\d{3})\)?\s?(\d{3})[-\s]?(\d{2})[-\s]?(\d{2})",
        r"+7 (\1) \2-\3-\4",
        text
    )

    # ❗ анти-склейка частых конструкций
    text = re.sub(
        r"([а-яё]{5,})(нам|вам|мы|вы|это|для|при|как)",
        r"\1 \2",
        text,
        flags=re.IGNORECASE
    )

    return text


# =========================
# 🧹 Удаление SEO / гео мусора
# =========================
def remove_seo_noise(text: str) -> str:
    """
    Удаляет:
    - гео списки (районы, шоссе)
    - SEO простыни
    """

    text_lower = text.lower()

    # ❌ слишком длинный блок = почти всегда SEO
    if len(text) > 800:
        return ""

    geo_keywords = [
        "административный округ",
        "район",
        "шоссе",
        "проспект",
        "мкад",
        "ттк",
        "области",
    ]

    hits = sum(1 for k in geo_keywords if k in text_lower)

    if hits >= 2:
        return ""

    # ❌ списки через •
    if "•" in text and len(text) > 200:
        return ""

    return text


# =========================
# 🧹 Нормализация текста
# =========================
def normalize_text(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "&nbsp;": " ",
        "&laquo;": "«",
        "&raquo;": "»",
        "&mdash;": "—",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # убираем лишние пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================
# 🧠 Финальная полировка
# =========================
def beautify_text(text: str) -> str:
    """
    Делает текст читаемым
    """

    # убираем повтор слов
    text = re.sub(r"\b(\w+)( \1\b)+", r"\1", text, flags=re.IGNORECASE)

    # 🔥 добавляем мини-абзацы
    text = re.sub(r"([А-ЯЁ][а-яё]+:)", r"\n\1", text)

    return text


# =========================
# 🧹 Основная очистка
# =========================
def clean_text(text: str) -> str:
    if not text:
        return ""

    text = remove_garbage(text)
    text = remove_spaced_letters(text)
    text = fix_spacing(text)
    text = remove_seo_noise(text)
    text = normalize_text(text)
    text = beautify_text(text)

    return text


# =========================
# 🚫 Фильтр мусора
# =========================
def is_garbage(text: str) -> bool:
    if not text:
        return True

    text_lower = text.lower()

    # короткий мусор
    if len(text) < 40:
        return True

    # формы
    if any(x in text_lower for x in [
        "ваше имя",
        "email",
        "отправить",
        "сохранить"
    ]):
        return True

    # слишком много цифр
    digits = len(re.findall(r"\d", text))
    if digits > 30:
        return True

    # мало букв
    letters = re.findall(r"[а-яА-Яa-zA-Z]", text)
    if len(letters) < 20:
        return True

    # SEO переспам
    words = text_lower.split()
    if len(words) > 20:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            return True

    return False


# =========================
# 🔄 Обработка блоков
# =========================
def process_content_block(content: list) -> list:

    cleaned = []

    logger.info("🧹 Очистка текстовых блоков (FINAL PRO)")

    for item in content:
        raw_text = item.get("text", "")

        text = clean_text(raw_text)

        if not text or is_garbage(text):
            continue

        cleaned.append({
            "type": item.get("type", "text"),
            "text": text,
            "title": item.get("title", ""),
            "url": item.get("url", "")
        })

    logger.info(f"✅ После очистки блоков: {len(cleaned)}")

    return cleaned
