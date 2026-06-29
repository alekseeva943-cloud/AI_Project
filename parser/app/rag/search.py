# Модуль поиска по векторному хранилищу
"""
search.py

Модуль отвечает за поиск и подготовку контекста для GPT.

Что делает:
1. Принимает запрос пользователя
2. Превращает его в embedding
3. Ищет релевантные чанки
4. Формирует контекст
5. Возвращает готовый текст для GPT

Важно:
Это связующее звено между базой и генерацией ответа.
"""

from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config.settings import TOP_K_RESULTS
from app.utils.logger import logger


# =========================
# 🧠 КЛАСС SEARCH ENGINE
# =========================
class SearchEngine:
    """
    Основной класс поиска.
    """

    def __init__(self):
        """
        Инициализация:
        - embedder
        - vector store (загружается)
        """

        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.vector_store.load()

        logger.info("🔍 SearchEngine инициализирован")

    # =========================
    # 🔍 Поиск
    # =========================

    def search(self, query: str) -> list:
        """
        Ищет релевантные чанки.

        Возвращает список результатов.
        """

        logger.info(f"🔎 Поиск: {query}")

        query_vector = self.embedder.get_embedding(query)

        results = self.vector_store.search(query_vector, k=TOP_K_RESULTS)

        logger.info(f"📊 Найдено результатов: {len(results)}")

        return results

    # =========================
    # 🧠 Сбор контекста
    # =========================

    def build_context(self, results: list) -> str:
        """
        Собирает текстовый контекст для GPT.

        Склеивает найденные чанки.
        """

        context_parts = []

        for i, item in enumerate(results, start=1):

            text = item.get("content", "")
            title = item.get("title")

            block = f"[{i}] {title if title else ''}\n{text}"

            context_parts.append(block)

        context = "\n\n".join(context_parts)

        logger.info("🧠 Контекст собран")

        return context

    # =========================
    # 🚀 Полный pipeline
    # =========================

    def get_context(self, query: str) -> str:
        """
        Полный процесс:
        запрос → поиск → контекст
        """

        results = self.search(query)

        context = self.build_context(results)

        return context
