# rag_service.py

import json
import logging

import faiss
import numpy as np
from openai import OpenAI
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"

TOP_K = 5
MAX_DISTANCE = 2.0

INDEX_PATH = "data/faiss.index"
METADATA_PATH = "data/metadata.json"

index = None
metadata = None


def load_rag_index():
    """
    Загружает индекс и метаданные в память.
    """

    global index
    global metadata

    index = faiss.read_index(INDEX_PATH)

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        metadata = json.load(f)


def reload_rag_index():
    """
    Перезагружает FAISS индекс без перезапуска бота.
    """

    try:

        load_rag_index()

        logger.info(
            "✅ RAG индекс успешно перезагружен"
        )

        return True

    except Exception:
        logger.exception(
            "Ошибка reload RAG"
        )

        return False


def rag_health_check() -> bool:

    try:

        if index is None:
            return False

        if metadata is None:
            return False

        if len(metadata) == 0:
            return False

        if index.ntotal == 0:
            return False

        return True

    except Exception:
        return False


def get_embedding(text: str):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding, dtype="float32")


def retrieve_context(query: str):
    """
    Выполняет поиск релевантных чанков
    в активной базе знаний.
    """

    if not rag_health_check():
        return None

    vector = get_embedding(query).reshape(1, -1)

    distances, indices = index.search(vector, TOP_K)

    chunks = []

    for i, dist in zip(indices[0], distances[0]):
        if i >= len(metadata):
            continue
        if dist > MAX_DISTANCE:
            continue
        chunks.append(metadata[i]["content"])

    return "\n\n".join(chunks) if chunks else None


load_rag_index()
