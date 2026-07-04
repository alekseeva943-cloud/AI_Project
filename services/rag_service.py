# rag_service.py

import json
import logging
import os

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
CHUNKS_PATH = "data/chunks_final.json"

chunks_data = None
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

    global chunks_data

    if os.path.exists(CHUNKS_PATH):

        with open(
            CHUNKS_PATH,
            "r",
            encoding="utf-8"
        ) as f:
            chunks_data = json.load(f)

    else:
        chunks_data = []


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

    # ======================================================
    # Для вопросов про полный список услуг расширяем поиск.
    # Иначе GPT видит только часть базы знаний.
    # ======================================================

    top_k = TOP_K

    service_queries = [
        "услуг",        
        "что вы делаете",
        "чем занимаетесь",
        "что оказываете",
        "какие работы выполняете"
    ]

    if any(
        phrase in query.lower()
        for phrase in service_queries
    ):
        top_k = 20

    distances, indices = index.search(
        vector,
        top_k
    )

    chunks = []

    for i, dist in zip(indices[0], distances[0]):
        if i >= len(metadata):
            continue
        if dist > MAX_DISTANCE:
            continue
        chunk_index = metadata[i]["chunk_index"]

        chunks.append(
            chunks_data[chunk_index]["content"]
        )

    return "\n\n".join(chunks) if chunks else None


load_rag_index()
