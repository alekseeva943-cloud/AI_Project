"""
pipeline.py

Главный модуль обработки данных.

Порядок:
crawler → extractor → cleaner → dedup → blocks → split → dedup → chunks → embeddings → store
"""

import os
import json

from app.parser.crawler import crawl
from app.parser.extractor import load_all_pages
from app.config.paths import OUTPUT_DIR

from app.processing.cleaner import process_content_block
from app.processing.deduplicator import Deduplicator
from app.processing.block_builder import build_blocks
from app.processing.splitter import process_blocks

from app.rag.chunker import Chunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore

from app.utils.logger import logger
from app.utils.cost_tracker import CostTracker


# =========================
# 🚀 PIPELINE
# =========================
def run_pipeline(progress_callback=None):

    tracker = CostTracker()
    deduplicator = Deduplicator()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # =========================
    # 🌐 CRAWLER
    # =========================
    logger.info("🌐 Запуск crawler")
    crawl(progress_callback)

    # =========================
    # 📂 LOAD
    # =========================
    if progress_callback:
        progress_callback("📂 Загрузка страниц...")

    pages = load_all_pages()

    if not pages:
        raise Exception("❌ Нет данных после парсинга")

    # =========================
    # 🧹 CLEAN
    # =========================
    if progress_callback:
        progress_callback("🧹 Очистка данных...")

    cleaned_pages = []

    for page in pages:
        cleaned = process_content_block(page.get("content", []))

        if not cleaned:
            continue

        cleaned_pages.append({
            "title": page.get("title") or "",
            "url": page.get("url") or "",
            "content": cleaned
        })

    # =========================
    # 🔁 DEDUP (внутри страницы)
    # =========================
    if progress_callback:
        progress_callback("🔁 Удаление дубликатов...")

    dedup_pages = []

    for page in cleaned_pages:
        unique = deduplicator.remove_duplicates(page["content"])

        if not unique:
            continue

        dedup_pages.append({
            "title": page["title"],
            "url": page["url"],
            "content": unique
        })

    # =========================
    # 🧱 BLOCKS (нормальные)
    # =========================
    if progress_callback:
        progress_callback("🧱 Формирование блоков...")

    all_blocks = []

    for page in dedup_pages:
        blocks = build_blocks(page["content"])

        for block in blocks:
            block["title"] = page["title"] or ""
            block["url"] = page["url"] or ""

        all_blocks.extend(blocks)

    # =========================
    # ✂️ SPLIT
    # =========================
    if progress_callback:
        progress_callback("✂️ Разбиение текста...")

    processed_blocks = process_blocks(all_blocks)

    # =========================
    # 🔁 ГЛОБАЛЬНЫЙ DEDUP
    # =========================
    seen = set()
    unique_blocks = []

    for block in processed_blocks:
        text = block.get("content", "")

        if isinstance(text, list):
            text = " ".join(text)

        text = text.strip()

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)

        block["content"] = text
        unique_blocks.append(block)

    processed_blocks = unique_blocks


# =========================
# 📄 TXT (читаемый!)
# =========================
    if progress_callback:
        progress_callback("📄 Сбор текста базы...")

    raw_text_parts = []
    last_title = None

    for block in processed_blocks:
        title = block.get("title") or ""
        text = block.get("content", "").strip()

        if not text:
            continue

        # 👉 Заголовок только при смене страницы
        if title and title != last_title:
            raw_text_parts.append(f"\n=== {title} ===")
            raw_text_parts.append("")  # отступ
            last_title = title

        # 👉 ВАЖНО: текст добавляется ВСЕГДА
        raw_text_parts.append(text)

    raw_text = "\n\n".join(raw_text_parts)

    # =========================
    # Сохраняем полный текст базы знаний
    #
    # Используется для:
    # - ручной проверки результата парсинга
    # - отладки чанкинга
    # - анализа качества очистки
    #
    # Файл не участвует в работе RAG напрямую.
    # =========================
    with open(
        OUTPUT_DIR / "raw_text.txt",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(raw_text)

    # =========================
    # 📦 CHUNKS
    # =========================
    if progress_callback:
        progress_callback("📦 Создание чанков...")

    chunker = Chunker()
    chunks = chunker.create_chunks(processed_blocks)

    # =========================
    # Сохраняем итоговые чанки.
    #
    # Это главный промежуточный артефакт RAG:
    #
    # - используется для проверки качества чанкинга;
    # - используется для отладки retrieval;
    # - может использоваться для повторной индексации
    #   без повторного парсинга сайта.
    # =========================
    with open(
        OUTPUT_DIR / "chunks_final.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            chunks,
            f,
            ensure_ascii=False,
            indent=2
        )

    # =========================
    # 🧠 TOKENS
    # =========================
    total_tokens = sum(chunk.get("tokens", 0) for chunk in chunks)
    tracker.add_tokens(total_tokens)

    # =========================
    # 🧠 EMBEDDINGS
    # =========================
    if progress_callback:
        progress_callback("🧠 Создание embeddings...")

    embedder = Embedder()
    embeddings, metadata = embedder.process_chunks(chunks)

    # =========================
    # Сохраняем metadata для FAISS.
    #
    # Metadata используется при retrieval:
    #
    # index -> metadata -> chunk
    #
    # Структура metadata является частью контракта
    # между parser и Telegram-ботом.
    #
    # Изменять формат без необходимости не рекомендуется.
    # =========================
    with open(
        OUTPUT_DIR / "metadata.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2
        )

    # =========================
    # 📦 VECTOR STORE
    # =========================
    if progress_callback:
        progress_callback("📦 Сохранение базы...")

    store = VectorStore()
    store.build(embeddings)
    store.set_metadata(metadata)
    store.save()

    # =========================
    # ✅ DONE
    # =========================
    if progress_callback:
        progress_callback("✅ Готово!")

    logger.info("🎉 Pipeline завершён")

    return {
        "pages": len(pages),
        "blocks": len(all_blocks),
        "chunks": len(chunks),
        "tokens": tracker.total_tokens,
        "usd": tracker.get_cost_usd(),
        "rub": tracker.get_cost_rub(),
    }
