# rag_service.py

import json
import faiss
import numpy as np
from openai import OpenAI
from config.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

EMBEDDING_MODEL = "text-embedding-3-small"

TOP_K = 5
MAX_DISTANCE = 2.0

INDEX_PATH = "data/faiss.index"
METADATA_PATH = "data/metadata.json"

index = faiss.read_index(INDEX_PATH)

with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)


def get_embedding(text: str):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding, dtype="float32")


def retrieve_context(query: str):
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
