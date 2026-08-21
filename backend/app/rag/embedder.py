from __future__ import annotations

import hashlib
import math
from functools import lru_cache

from app.core.config import settings


def embedding_status() -> dict:
    return {
        "bge_enabled": settings.bge_enabled,
        "embedding_backend": settings.embedding_backend,
        "bge_model_path": settings.bge_model_path or "",
        "available": _model_available() or settings.embedding_backend == "local_hash",
    }


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Return embeddings when an optional backend is available.

    Default configuration returns None, so the system continues with BM25.
    `local_hash` is a lightweight development fallback for exercising vector
    flow without installing a BGE model.
    """
    if settings.embedding_backend == "local_hash":
        return [_hash_embedding(text) for text in texts]

    model = _load_bge_model()
    if model is None:
        return None
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [list(map(float, row)) for row in embeddings]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _model_available() -> bool:
    return _load_bge_model() is not None


@lru_cache
def _load_bge_model():
    if not settings.bge_enabled or not settings.bge_model_path:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.bge_model_path)
    except Exception:
        return None


def _hash_embedding(text: str, dims: int = 64) -> list[float]:
    vector = [0.0] * dims
    tokens = [token for token in _tokenize(text) if token]
    for token in tokens:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = digest[0] % dims
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0:
        return vector
    return [item / norm for item in vector]


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = []
    current = []
    for char in text:
        if char.isalnum() or "\u4e00" <= char <= "\u9fff":
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens
