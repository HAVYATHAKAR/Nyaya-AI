"""Embedding + vector store service for RAG.

Uses a lightweight local embedding (hash-based) for MVP. The hash-based
embedding is deterministic but NOT semantically meaningful — for production
swap in `sentence-transformers` with BAAI/bge-small-en-v1.5.

The KB is stored in-memory (Python list). For production, use Qdrant Cloud.
"""
import hashlib
from typing import List, Dict, Any
from loguru import logger

from ..core.config import settings


class EmbeddingService:
    """Deterministic hash-based embeddings for MVP. 384-dim to match bge-small."""

    DIM = 384

    def encode(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_embed(t) for t in texts]

    def encode_one(self, text: str) -> List[float]:
        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> List[float]:
        """Deterministic hash-based pseudo-embedding.

        NOTE: This is a placeholder for MVP demos where the real bge-small
        model can't be downloaded. It returns a 384-dim vector that's stable
        per input but NOT semantically meaningful. For real RAG, swap in
        sentence-transformers with BAAI/bge-small-en-v1.5.
        """
        # Use multiple hash windows to fill the dim
        vec = [0.0] * self.DIM
        for i in range(self.DIM):
            h = hashlib.md5(f"{i}:{text}".encode()).hexdigest()
            vec[i] = (int(h[:8], 16) / 0xFFFFFFFF) * 2 - 1  # range [-1, 1]
        # L2 normalize
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class VectorStore:
    """In-memory vector store with cosine similarity search.

    For production, replace with Qdrant Cloud:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    """

    def __init__(self):
        self._store: List[Dict[str, Any]] = []

    def upsert(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        for c, e in zip(chunks, embeddings):
            # Replace if id exists, else append
            self._store = [s for s in self._store if s["id"] != c["id"]]
            self._store.append({**c, "embedding": e})
        logger.info(f"Vector store now holds {len(self._store)} chunks")

    def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not self._store:
            return []
        # Cosine similarity (vectors are already normalized)
        scored = []
        for item in self._store:
            e = item["embedding"]
            sim = sum(a * b for a, b in zip(query_embedding, e))
            scored.append((sim, item))
        scored.sort(key=lambda x: -x[0])
        return [
            {
                "text": item["text"],
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "score": float(sim),
            }
            for sim, item in scored[:top_k]
        ]


# Singletons
embedding_service = EmbeddingService()
vector_store = VectorStore()
