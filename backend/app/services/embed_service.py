"""Real sentence embeddings and persistent Qdrant storage; never fall back to RAM."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from ..core.config import settings


class EmbeddingService:
    def __init__(self):
        self._model = None
        self._dimension: int | None = None

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
                self._dimension = int(self._model.get_sentence_embedding_dimension())
            except Exception as exc:
                self._model = None
                logger.warning("Semantic embedding model unavailable ({})", type(exc).__name__)
                raise RuntimeError("Semantic embedding model could not be loaded") from exc
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._get_model().encode(texts, normalize_embeddings=True).tolist()
        if not vectors or any(not vector or len(vector) != self._dimension for vector in vectors):
            raise RuntimeError("Embedding model returned an invalid vector dimension")
        return vectors

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        self._get_model()
        assert self._dimension is not None
        return self._dimension


class VectorStore:
    """Persistent Qdrant adapter (local disk in development, remote server when configured)."""

    def __init__(self):
        self._client = None
        self._client_mode: str | None = None

    def _mode(self) -> str | None:
        if settings.qdrant_url:
            if settings.app_env.lower() not in {"development", "dev", "test"} and not settings.qdrant_api_key:
                return None
            return "server"
        if settings.app_env.lower() in {"development", "dev", "test"}:
            return "local"
        return None

    @property
    def configured(self) -> bool:
        return self._mode() is not None

    def _get_client(self):
        mode = self._mode()
        if mode is None:
            raise RuntimeError("Persistent Qdrant storage is not configured")
        if self._client is not None and self._client_mode == mode:
            return self._client
        try:
            from qdrant_client import QdrantClient
            if mode == "server":
                self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=10)
            else:
                path = Path(settings.qdrant_local_path)
                path.mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=str(path))
            self._client_mode = mode
            return self._client
        except Exception as exc:
            self._client = None
            logger.warning("Persistent Qdrant storage unavailable ({})", type(exc).__name__)
            raise RuntimeError("Persistent Qdrant storage is unavailable") from exc

    def _collection_exists(self, client) -> bool:
        try:
            return bool(client.collection_exists(settings.qdrant_collection))
        except AttributeError:
            return settings.qdrant_collection in {item.name for item in client.get_collections().collections}

    def _check_dimension(self, client, dimension: int) -> bool:
        if not self._collection_exists(client):
            return False
        info = client.get_collection(settings.qdrant_collection)
        params = info.config.params.vectors
        if isinstance(params, dict):
            values = [v.size for v in params.values()]
            matches = dimension in values
        else:
            matches = params.size == dimension
        if not matches:
            raise RuntimeError("Qdrant collection dimension does not match the configured embedding model")
        return True

    def status(self, dimension: int) -> str:
        if not self.configured:
            return "unavailable_storage"
        try:
            client = self._get_client()
            if not self._check_dimension(client, dimension):
                return "unavailable_empty_index"
            return "available" if self.count() > 0 else "unavailable_empty_index"
        except Exception as exc:
            logger.info("Qdrant readiness check failed ({})", type(exc).__name__)
            return "unavailable_index"

    def count(self) -> int:
        client = self._get_client()
        if not self._collection_exists(client):
            return 0
        result = client.count(collection_name=settings.qdrant_collection, exact=True)
        return int(result.count)

    def upsert(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Each passage must have exactly one embedding")
        if not chunks:
            return
        dimensions = {len(vector) for vector in embeddings}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("Embedding dimensions are inconsistent or empty")
        dimension = dimensions.pop()
        client = self._get_client()
        if not self._collection_exists(client):
            from qdrant_client.models import Distance, VectorParams
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )
        else:
            self._check_dimension(client, dimension)
        from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue, PointStruct
        # Replace prior versions of the same source so changed official text cannot remain retrievable.
        source_ids = {str(chunk["source_id"]) for chunk in chunks}
        for source_id in source_ids:
            client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=FilterSelector(filter=Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))])),
            )
        points = []
        for chunk, vector in zip(chunks, embeddings):
            if len(vector) != dimension:
                raise ValueError("Embedding dimensions are inconsistent")
            payload = {key: value for key, value in chunk.items() if key != "id"}
            points.append(PointStruct(id=chunk["id"], vector=vector, payload=payload))
        client.upsert(collection_name=settings.qdrant_collection, points=points, wait=True)
        logger.info("Persisted {} legal passages to Qdrant", len(points))

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        client = self._get_client()
        if not self._check_dimension(client, len(query_embedding)):
            return []
        from qdrant_client.models import FieldCondition, Filter, MatchValue
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_embedding,
            query_filter=Filter(must=[
                FieldCondition(key="jurisdiction", match=MatchValue(value="India")),
                FieldCondition(key="review_status", match=MatchValue(value="reviewed")),
            ]),
            limit=top_k,
            with_payload=True,
        )
        hits = []
        for point in response.points:
            payload = dict(point.payload or {})
            hits.append({"id": str(point.id), **payload, "score": float(point.score)})
        return hits


embedding_service = EmbeddingService()
vector_store = VectorStore()
