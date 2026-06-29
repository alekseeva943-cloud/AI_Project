# Модуль создания эмбеддингов с использованием OpenAI embeddings
"""
embedder.py

Модуль отвечает за создание embeddings (векторных представлений текста).

Что делает:
1. Берёт чанки текста
2. Отправляет их в OpenAI
3. Получает вектора (embeddings)
4. Формирует metadata (БЕЗ текста)
"""

from openai import OpenAI
import numpy as np

from app.config.settings import EMBEDDING_MODEL
from app.utils.logger import logger

from dotenv import load_dotenv

load_dotenv()

# =========================
# 🧠 КЛАСС EMBEDDER
# =========================
class Embedder:
    """
    Класс для работы с embeddings.
    """

    def __init__(self):
        """
        Инициализация клиента OpenAI.
        """
        self.client = OpenAI()
        logger.info(f"🧠 Embedder инициализирован: {EMBEDDING_MODEL}")

    # =========================
    # 🔢 Получение embedding
    # =========================
    def get_embedding(self, text: str) -> list:
        """
        Получает embedding для одного текста.
        """
        response = self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )

        return response.data[0].embedding

    # =========================
    # 📦 Обработка всех чанков
    # =========================
    def process_chunks(self, chunks: list) -> tuple:
        """
        Создаёт embeddings для всех чанков.

        ВАЖНО:
        - metadata строго соответствует embeddings
        - индексы идут подряд без пропусков
        """

        logger.info("🧠 Начинаем создание embeddings")

        embeddings = []
        metadata = []

        valid_index = 0  # 👈 ключевой фикс

        for i, chunk in enumerate(chunks):

            text = chunk.get("content", "").strip()

            # ❗ пропускаем пустые чанки
            if not text:
                continue

            try:
                emb = self.get_embedding(text)

                embeddings.append(emb)

                metadata.append({
                    "id": valid_index,
                    "chunk_index": valid_index,
                    "title": chunk.get("title", ""),
                    "url": chunk.get("url", ""),
                    "type": chunk.get("type", "text")
                })

                valid_index += 1  # 👈 увеличиваем только если реально добавили

            except Exception as e:
                logger.error(f"❌ Ошибка embedding на чанке {i}: {e}")
                continue

            if valid_index % 10 == 0:
                logger.info(f"📊 Обработано чанков: {valid_index}")

        embeddings = np.array(embeddings).astype("float32")

        logger.info(f"✅ Embeddings созданы: {len(embeddings)}")

        return embeddings, metadata
