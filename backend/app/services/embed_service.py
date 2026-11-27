"""Optional real embeddings; semantic retrieval is disabled unless configured."""
from typing import Any, Dict, List
from loguru import logger
from ..core.config import settings


class EmbeddingService:
    def __init__(self):
        self._model = None

    @property
    def available(self) -> bool:
        return settings.embedding_enabled and bool(settings.embed_model)

    def _get_model(self):
        if not self.available:
            raise RuntimeError("Semantic retrieval is disabled; configure EMBEDDING_ENABLED and EMBED_MODEL")
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.embed_model)
            except Exception as exc:
                logger.warning("Semantic embedding model unavailable ({})", type(exc).__name__)
                raise RuntimeError("Semantic embedding model could not be loaded") from exc
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        return self._get_model().encode(texts, normalize_embeddings=True).tolist()

    def encode_one(self, text: str) -> List[float]:
        return self.encode([text])[0]


class VectorStore:
    """Process-local index for actual sentence-transformers vectors only."""

    def __init__(self):
        self._store: List[Dict[str, Any]] = []

    def upsert(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        if len(chunks) != len(embeddings):
            raise ValueError("Each passage must have exactly one embedding")
        by_id = {item["id"]: item for item in self._store}
        for chunk, embedding in zip(chunks, embeddings):
            by_id[chunk["id"]] = {**chunk, "embedding": embedding}
        self._store = list(by_id.values())
        logger.info("Local semantic index contains {} passages", len(self._store))

    def search(
        self, query_embedding: List[float], top_k: int = 5
    ) -> List[Dict[str, Any]]:
        scored = []
        for item in self._store:
            e = item["embedding"]
            if len(query_embedding) != len(e):
                continue
            sim = sum(a * b for a, b in zip(query_embedding, e))
            scored.append((sim, item))
        scored.sort(key=lambda x: -x[0])
        return [
            {
                "id": item.get("id"),
                "text": item.get("text", ""),
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "source_url": item.get("source_url", ""),
                "jurisdiction": item.get("jurisdiction", ""),
                "score": float(sim),
            }
            for sim, item in scored[:top_k]
        ]


# Singletons
embedding_service = EmbeddingService()
vector_store = VectorStore()
