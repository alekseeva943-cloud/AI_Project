"""
extractor.py

Модуль отвечает за извлечение структурированного контента из HTML.

Что делает:
1. Читает HTML файлы из папки RAW_HTML_DIR
2. Удаляет мусор (script, style, nav и т.д.)
3. Извлекает контент (h1, h2, p, li)
4. Извлекает TITLE
5. Извлекает URL (правильно, без костылей)
6. Возвращает чистые страницы для pipeline

ВАЖНО:
- URL берём из HTML (canonical / og:url)
- если нет → fallback на имя файла (временное решение)
"""

import os
from bs4 import BeautifulSoup

from app.config.settings import RAW_HTML_DIR
from app.utils.logger import logger


# =========================
# 🧹 Удаление мусора
# =========================
def remove_noise(soup):
    """
    Удаляем ненужные теги, чтобы не тянуть мусор в базу.
    """
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()


# =========================
# 🔗 Извлечение URL
# =========================
def extract_url(soup, fallback_filename="") -> str:
    """
    Пытаемся получить реальный URL страницы.

    Порядок приоритета:
    1. <link rel="canonical">
    2. <meta property="og:url">
    3. fallback → имя файла
    """

    # ✅ canonical — самый правильный источник
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        return canonical.get("href").strip()

    # ✅ og:url — соц. разметка
    og = soup.find("meta", property="og:url")
    if og and og.get("content"):
        return og.get("content").strip()

    # ⚠ fallback (лучше чем пусто)
    return fallback_filename


# =========================
# 📄 Извлечение контента
# =========================
def extract_content(html: str) -> list:
    """
    Достаём текстовые блоки из HTML.
    """

    soup = BeautifulSoup(html, "html.parser")
    remove_noise(soup)

    content = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(strip=True)

        if not text:
            continue

        content.append({
            "type": tag.name,
            "text": text
        })

    return content


# =========================
# 🏷 Title
# =========================
def extract_title(soup) -> str:
    """
    Извлекаем title страницы.
    """

    if soup.title:
        return soup.title.get_text(strip=True)

    return ""


# =========================
# 📁 Чтение всех HTML файлов
# =========================
def load_all_pages() -> list:
    """
    Читает все HTML файлы из папки RAW_HTML_DIR
    и превращает их в структурированные страницы.

    Возвращает:
    [
        {
            "title": "...",
            "url": "...",
            "content": [...]
        }
    ]
    """

    logger.info("📂 Загрузка HTML файлов")

    pages = []

    if not os.path.exists(RAW_HTML_DIR):
        logger.warning("❗ Папка raw_html не найдена")
        return pages

    files = os.listdir(RAW_HTML_DIR)

    for i, filename in enumerate(files, start=1):

        path = os.path.join(RAW_HTML_DIR, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()

            soup = BeautifulSoup(html, "html.parser")

            # 🔹 извлекаем данные
            title = extract_title(soup)
            url = extract_url(soup, fallback_filename=filename)
            content = extract_content(html)

            # 🔹 пропускаем пустые страницы
            if not content:
                continue

            pages.append({
                "title": title or "",
                "url": url or "",
                "content": content
            })

            logger.info(f"📄 Загружен файл {i}: {filename}")

        except Exception as e:
            logger.error(f"❌ Ошибка чтения {filename}: {e}")

    logger.info(f"✅ Всего страниц: {len(pages)}")

    return pages
