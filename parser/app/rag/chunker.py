"""
chunker.py

Модуль отвечает за формирование финальных чанков для embeddings.

Что делает:
1. Берёт обработанные блоки
2. Считает токены
3. Собирает чанки с ограничением
4. СОХРАНЯЕТ метаданные (ВАЖНО!)
"""

from app.config.settings import MAX_TOKENS
from app.utils.logger import logger
from app.rag.tokenizer import Tokenizer


class Chunker:
    def __init__(self):
        self.tokenizer = Tokenizer()
        logger.info("🧠 Chunker инициализирован")

    def normalize_content(self, content):
        if isinstance(content, list):
            return " ".join(content)
        return content

    def create_chunks(self, blocks: list) -> list:

        logger.info("📦 Начинаем сборку чанков")

        chunks = []

        current_chunk = []
        current_tokens = 0

        # 👉 ВАЖНО: будем хранить мету чанка
        current_meta = {
            "type": None,
            "title": None,
            "url": None
        }

        for block in blocks:

            text = self.normalize_content(block["content"])
            tokens = self.tokenizer.count(text)

            # =========================
            # 🚨 БОЛЬШОЙ БЛОК
            # =========================
            if tokens > MAX_TOKENS:
                chunks.append({
                    "content": text,
                    "tokens": tokens,
                    "type": block.get("type"),
                    "title": block.get("title"),
                    "url": block.get("url"),
                })
                continue

            # =========================
            # 📦 НЕ ВЛЕЗАЕТ → СОХРАНЯЕМ
            # =========================
            if current_tokens + tokens > MAX_TOKENS:

                chunks.append({
                    "content": " ".join(current_chunk),
                    "tokens": current_tokens,
                    "type": current_meta["type"],
                    "title": current_meta["title"],
                    "url": current_meta["url"],
                })

                current_chunk = []
                current_tokens = 0
                current_meta = {
                    "type": None,
                    "title": None,
                    "url": None
                }

            # =========================
            # ➕ ДОБАВЛЯЕМ В ЧАНК
            # =========================
            current_chunk.append(text)
            current_tokens += tokens

            # 👉 сохраняем мету (берём первую осмысленную)
            if current_meta["title"] is None:
                current_meta["type"] = block.get("type")
                current_meta["title"] = block.get("title")
                current_meta["url"] = block.get("url")

        # =========================
        # 📦 ПОСЛЕДНИЙ ЧАНК
        # =========================
        if current_chunk:
            chunks.append({
                "content": " ".join(current_chunk),
                "tokens": current_tokens,
                "type": current_meta["type"],
                "title": current_meta["title"],
                "url": current_meta["url"],
            })

        logger.info(f"✅ Чанков создано: {len(chunks)}")

        return chunks
