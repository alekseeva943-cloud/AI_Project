"""
crawler.py

Модуль обхода сайта (DFS).

Что делает:
1. Стартует с BASE_URL
2. Обходит сайт
3. Фильтрует мусор
4. НЕ добавляет битые ссылки
5. Убирает дубли (включая / и без /)
6. Сохраняет HTML
7. Отправляет корректный прогресс
"""

import time
import os
import shutil
import requests
import hashlib

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from app.config.settings import (
    BASE_URL,
    CRAWL_LIMIT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    SAVE_HTML,
    RAW_HTML_DIR,
)

from app.utils.logger import logger


# =========================
# 🔧 НОРМАЛИЗАЦИЯ URL
# =========================
def normalize_url(url: str) -> str:
    """
    Приводит URL к единому виду:
    - убирает /
    - убирает якоря
    """
    url = url.split("#")[0]
    return url.rstrip("/")


# =========================
# 🔑 Генерация имени файла
# =========================
def generate_filename(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


# =========================
# 🔍 Проверка внутренней ссылки
# =========================
def is_internal(url: str) -> bool:
    return urlparse(url).netloc == urlparse(BASE_URL).netloc


# =========================
# 🌐 Получение HTML страницы
# =========================
def get_html(url: str) -> str | None:
    try:
        logger.info(f"🌐 Запрос страницы: {url}")

        response = requests.get(url, timeout=REQUEST_TIMEOUT)

        # ❗ пропускаем не 200
        if response.status_code != 200:
            logger.warning(f"⚠️ Пропуск (не 200): {url}")
            return None

        return response.text

    except Exception as e:
        logger.error(f"❌ Ошибка при запросе {url}: {e}")
        return None


# =========================
# 🔗 Извлечение ссылок
# =========================
def extract_links(html: str, current_url: str) -> set:
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # 🚫 мусор
        if href.startswith("#"):
            continue

        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue

        full_url = urljoin(current_url, href)

        # 🌐 только внутренние
        if not is_internal(full_url):
            continue

        # 🚫 файлы
        if full_url.lower().endswith((
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx",
            ".zip", ".rar", ".mp4", ".mp3"
        )):
            continue

        clean_url = normalize_url(full_url)

        links.add(clean_url)

    return links


# =========================
# 💾 Сохранение HTML
# =========================
def save_html(url, html):
    os.makedirs(RAW_HTML_DIR, exist_ok=True)

    filename = generate_filename(url)
    path = f"{RAW_HTML_DIR}/{filename}.html"

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"💾 Сохранено: {filename}")


# =========================
# 🧹 Очистка старых данных
# =========================
def clear_storage():
    if os.path.exists(RAW_HTML_DIR):
        shutil.rmtree(RAW_HTML_DIR)

    os.makedirs(RAW_HTML_DIR, exist_ok=True)

    logger.info("🧹 Старые HTML удалены")


# =========================
# 🕷 Основной crawl
# =========================
def crawl(progress_callback=None) -> list:

    clear_storage()

    visited = set()
    to_visit = [normalize_url(BASE_URL)]
    results = []

    page_count = 0

    logger.info("🚀 Начало обхода сайта")

    while to_visit and page_count < CRAWL_LIMIT:

        url = normalize_url(to_visit.pop())

        # ❗ защита от дублей
        if url in visited:
            continue

        logger.info(f"📄 Парсим страницу {page_count + 1}: {url}")

        # 👉 прогресс (только номер страницы)
        if progress_callback:
            progress_callback(f"🌐 Парсинг страницы {page_count + 1}")

        html = get_html(url)

        # ❗ если битая — не считаем страницей
        if not html:
            visited.add(url)
            continue

        visited.add(url)

        page_count += 1
        results.append(url)

        if SAVE_HTML:
            save_html(url, html)

        # 👉 достаём ссылки
        links = extract_links(html, url)

        for link in links:
            if link not in visited and link not in to_visit:
                to_visit.append(link)

        time.sleep(REQUEST_DELAY)

    logger.info(f"✅ Обход завершён. Страниц: {len(results)}")

    if progress_callback:
        progress_callback(f"✅ Спарсено страниц: {len(results)}")

    return results
