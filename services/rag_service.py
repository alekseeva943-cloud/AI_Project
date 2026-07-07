# services/rag_service.py

"""
Работа с RAG (Retrieval-Augmented Generation).

Назначение:
- загрузка FAISS-индекса;
- загрузка метаданных базы знаний;
- получение эмбеддингов запросов;
- поиск релевантных чанков;
- проверка состояния RAG.
"""

import json
import logging
import os

import faiss
import numpy as np
from openai import OpenAI

from config.config import OPENAI_API_KEY


# ==========================================================
# Клиент OpenAI.
# ==========================================================

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================================
# Логгер модуля.
# ==========================================================

logger = logging.getLogger(__name__)

# ==========================================================
# Константы модуля.
# ==========================================================

# Модель для построения эмбеддингов.
EMBEDDING_MODEL = "text-embedding-3-small"

# Количество чанков, возвращаемых при обычном поиске.
TOP_K = 5

# Максимально допустимое расстояние
# между запросом и найденным чанком.
MAX_DISTANCE = 2.0

# Путь к FAISS-индексу.
INDEX_PATH = "data/faiss.index"

# Путь к метаданным индекса.
METADATA_PATH = "data/metadata.json"

# Путь к исходным чанкам базы знаний.
CHUNKS_PATH = "data/chunks_final.json"

# ==========================================================
# Глобальные объекты.
# ==========================================================

# Загруженные чанки базы знаний.
chunks_data = None

# Активный FAISS-индекс.
index = None

# Метаданные индекса.
metadata = None


# ==========================================================
# Работа с индексом.
# ==========================================================

def load_rag_index() -> None:
    """
    Загружает FAISS-индекс и связанные
    с ним данные в память.

    Returns:
        None.
    """

    global index
    global metadata
    global chunks_data

    index = faiss.read_index(INDEX_PATH)

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    if os.path.exists(CHUNKS_PATH):

        with open(
            CHUNKS_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            chunks_data = json.load(file)

    else:
        chunks_data = []


def reload_rag_index() -> bool:
    """
    Перезагружает индекс без
    перезапуска приложения.

    Returns:
        bool.
    """

    try:
        load_rag_index()

        logger.info(
            "✅ RAG-индекс успешно перезагружен."
        )

        return True

    except Exception:
        logger.exception(
            "Ошибка при перезагрузке RAG-индекса."
        )
        return False


def rag_health_check() -> bool:
    """
    Проверяет готовность RAG
    к выполнению поиска.

    Returns:
        bool.
    """

    try:
        return (
            index is not None
            and metadata is not None
            and len(metadata) > 0
            and index.ntotal > 0
        )

    except Exception:
        return False


# ==========================================================
# Работа с эмбеддингами.
# ==========================================================

def get_embedding(
    text: str,
) -> np.ndarray:
    """
    Создаёт эмбеддинг текста.

    Returns:
        numpy.ndarray.
    """

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return np.array(
        response.data[0].embedding,
        dtype="float32",
    )


# ==========================================================
# Поиск контекста.
# ==========================================================

def retrieve_context(
    query: str,
) -> str | None:
    """
    Выполняет поиск наиболее
    релевантных фрагментов базы знаний.

    Returns:
        str | None.
    """

    if not rag_health_check():
        return None

    vector = get_embedding(query).reshape(1, -1)

    top_k = TOP_K

    # Для запросов о полном перечне услуг
    # расширяем область поиска.
    service_queries = [
        "услуг",
        "что вы делаете",
        "чем занимаетесь",
        "что оказываете",
        "какие работы выполняете",
    ]

    if any(
        phrase in query.lower()
        for phrase in service_queries
    ):
        top_k = 20

    distances, indices = index.search(
        vector,
        top_k,
    )

    chunks = []

    for chunk_id, distance in zip(
        indices[0],
        distances[0],
    ):
        if chunk_id >= len(metadata):
            continue

        if distance > MAX_DISTANCE:
            continue

        chunk_index = metadata[chunk_id]["chunk_index"]

        chunks.append(
            chunks_data[chunk_index]["content"]
        )

    if not chunks:
        return None

    return "\n\n".join(chunks)


# ==========================================================
# Первичная загрузка индекса.
# ==========================================================

load_rag_index()