# Модуль работы с FAISS для векторного хранилища
"""
vector_store.py

Модуль отвечает за работу с векторной базой (FAISS).

Что делает:
1. Создаёт индекс
2. Добавляет embeddings
3. Сохраняет индекс
4. Загружает индекс
5. Выполняет поиск

Важно:
Это слой хранения и поиска, НЕ генерации ответа.
"""

import faiss
import numpy as np
import json

from app.config.settings import (
    FAISS_INDEX_FILE,
    METADATA_FILE,
    EMBEDDING_DIMENSION
)

from app.utils.logger import logger


# =========================
# 🧠 КЛАСС VECTOR STORE
# =========================
class VectorStore:
    """
    Класс для работы с FAISS индексом.
    """

    def __init__(self):
        """
        Инициализация.
        """

        self.index = None
        self.metadata = []

        logger.info("🧠 VectorStore инициализирован")

    # =========================
    # 📦 Создание индекса
    # =========================

    def build(self, embeddings: np.ndarray):
        """
        Создаёт FAISS индекс и добавляет вектора.
        """

        logger.info("📦 Создание FAISS индекса")

        dim = embeddings.shape[1]

        # создаём индекс
        self.index = faiss.IndexFlatL2(dim)

        # добавляем вектора
        self.index.add(embeddings)

        logger.info(f"✅ Векторов добавлено: {len(embeddings)}")

    # =========================
    # 💾 Сохранение
    # =========================

    def save(self):
        """
        Сохраняет индекс и метаданные.
        """

        if self.index is None:
            raise ValueError("Индекс не создан")

        faiss.write_index(self.index, FAISS_INDEX_FILE)

        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        logger.info("💾 Индекс и метаданные сохранены")

    # =========================
    # 📥 Загрузка
    # =========================

    def load(self):
        """
        Загружает индекс и метаданные.
        """

        self.index = faiss.read_index(FAISS_INDEX_FILE)

        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        logger.info("📥 Индекс и метаданные загружены")

    # =========================
    # 🔍 Поиск
    # =========================

    def search(self, query_vector: np.ndarray, k: int = 3) -> list:
        """
        Ищет ближайшие вектора.

        На вход:
        - query_vector (вектор запроса)
        - k (сколько результатов вернуть)

        На выход:
        список метаданных
        """

        if self.index is None:
            raise ValueError("Индекс не загружен")

        # FAISS требует 2D массив
        query_vector = np.array([query_vector]).astype("float32")

        distances, indices = self.index.search(query_vector, k)

        results = []

        for idx in indices[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])

        return results

    # =========================
    # 📎 Добавление метаданных
    # =========================

    def set_metadata(self, metadata: list):
        """
        Сохраняет метаданные (тексты, url и т.д.)
        """

        self.metadata = metadata
