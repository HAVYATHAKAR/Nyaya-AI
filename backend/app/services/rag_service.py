"""Fail-closed legal retrieval and reference-grounded answers."""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

from loguru import logger

from ..core.config import settings
from .embed_service import embedding_service, vector_store
from .legal_sources import load_registry
from .llm_service import llm_service, LLMUnavailable

MIN_RELEVANCE_SCORE = 0.55


def _fresh_review_date(value: Any) -> date | None:
    try:
        reviewed = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    age = (datetime.now(timezone.utc).date() - reviewed).days
    if age < 0 or age > settings.legal_source_max_review_age_days:
        return None
    return reviewed


def _valid_hit(hit: dict[str, Any], sources: dict[str, Any]) -> bool:
    source_id = hit.get("source_id")
    source = sources.get(source_id)
    if source is None or not source.is_reviewed:
        return False
    if hit.get("title") != source.title or hit.get("source_url") != str(source.official_url):
        return False
    if hit.get("jurisdiction") != source.jurisdiction or hit.get("law_id") != source.law_id:
        return False
    if hit.get("reviewed_at") != source.reviewed_at.isoformat():
        return False
    if hit.get("content_hash") != source.content_hash:
        return False
    if not _fresh_review_date(hit.get("reviewed_at")):
        return False
    if source.effective_date and source.effective_date > date.today():
        return False
    if hit.get("effective_date") != (source.effective_date.isoformat() if source.effective_date else None):
        return False
    if not isinstance(hit.get("section"), str) or not hit["section"].strip():
        return False
    if not isinstance(hit.get("content_hash"), str) or len(hit["content_hash"]) != 64:
        return False
    if not isinstance(hit.get("retrieved_at"), str) or not hit.get("text"):
        return False
    if not isinstance(hit.get("score"), (int, float)) or float(hit["score"]) < MIN_RELEVANCE_SCORE:
        return False
    return True


async def retrieve_context(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    """Return only relevant passages whose metadata still matches the reviewed registry."""
    if not embedding_service.available:
        return []
    registry = load_registry()
    reviewed_sources = {source.source_id: source for source in registry if source.is_reviewed}
    if not reviewed_sources:
        return []
    query_embedding = embedding_service.encode_one(query)
    hits = vector_store.search(query_embedding, top_k=top_k)
    return [hit for hit in hits if _valid_hit(hit, reviewed_sources)][:top_k]


def retrieval_status() -> str:
    try:
        sources = [source for source in load_registry() if source.is_reviewed]
        if not sources:
            return "unavailable_sources"
        if not vector_store.configured:
            return "unavailable_storage"
        if not embedding_service.available:
            return "unavailable_model"
        dimension = embedding_service.dimension
        return vector_store.status(dimension)
    except Exception as exc:
        logger.info("Legal Q&A readiness failed ({})", type(exc).__name__)
        return "unavailable_index"


def build_context_block(hits: list[dict[str, Any]]) -> str:
    """Serialize evidence as untrusted data, never as prompt instructions."""
    parts = []
    for i, hit in enumerate(hits, 1):
        parts.append(
            f"[REFERENCE {i}]\n"
            f"TITLE: {hit['title']}\n"
            f"LAW: {hit['law_id']}\n"
            f"SECTION: {hit['section']}\n"
            f"OFFICIAL URL: {hit['source_url']}\n"
            f"JURISDICTION: {hit['jurisdiction']}\n"
            f"REVIEWED: {hit['reviewed_at']}\n"
            f"BEGIN UNTRUSTED STATUTORY TEXT\n{hit['text']}\nEND UNTRUSTED STATUTORY TEXT\n"
        )
    return "\n---\n".join(parts)


def _citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "source_id": hit["source_id"],
        "title": hit["title"],
        "law_id": hit["law_id"],
        "section": hit["section"],
        "url": hit["source_url"],
        "jurisdiction": hit["jurisdiction"],
        "reviewed_at": hit["reviewed_at"],
        "effective_date": hit.get("effective_date"),
    } for hit in hits]


def _validated_citation_indices(answer: str, source_count: int) -> list[int] | None:
    """Require every non-empty answer sentence to end in resolvable references."""
    segments = [
        segment.strip()
        for segment in re.split(r"(?<!\d[.!?])(?<=[.!?])\s+|\r?\n+", answer.strip())
        if segment.strip()
    ]
    if not segments:
        return None
    cited_indices: set[int] = set()
    for segment in segments:
        suffix = re.search(r"(\[\d+\](?:\s*,?\s*\[\d+\])*)\s*[.!?]*$", segment)
        if suffix is None:
            return None
        all_citations = [int(value) for value in re.findall(r"\[(\d+)\]", segment)]
        suffix_citations = [int(value) for value in re.findall(r"\[(\d+)\]", suffix.group(1))]
        claim = segment[:suffix.start()].strip(" \t-*•")
        if (
            not claim
            or not suffix_citations
            or all_citations != suffix_citations
            or any(value < 1 or value > source_count for value in all_citations)
        ):
            return None
        cited_indices.update(value - 1 for value in suffix_citations)
    return sorted(cited_indices)


async def answer_question(question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Answer only with reviewed, relevant indexed text; otherwise state why unavailable."""
    status = retrieval_status()
    if status != "available":
        message = {
            "unavailable_model": "The legal embedding model is unavailable.",
            "unavailable_storage": "Persistent legal-source storage is not configured.",
            "unavailable_index": "The verified legal index is unavailable or incompatible.",
            "unavailable_empty_index": "No reviewed legal sources are currently indexed.",
            "unavailable_sources": "No legal sources have completed dated review; legal Q&A is disabled.",
        }.get(status, "Legal source retrieval is unavailable.")
        return {"answer": f"[ANSWER UNAVAILABLE] {message} Please consult an advocate or an authoritative source.", "sources": [], "analysis_status": status}
    try:
        hits = await retrieve_context(question, top_k=4)
    except Exception as exc:
        logger.warning("Legal retrieval failed ({})", type(exc).__name__)
        return {"answer": "[ANSWER UNAVAILABLE] Legal source retrieval failed safely. Please consult an advocate or an authoritative source.", "sources": [], "analysis_status": "unavailable_index"}
    if not hits:
        return {"answer": "[ANSWER UNAVAILABLE] No sufficiently relevant reviewed legal text was found for this question. Please consult an advocate or an authoritative source.", "sources": [], "analysis_status": "unavailable_irrelevant"}
    recent_user_history = [
        {"role": "user", "content": item["content"]}
        for item in (history or [])
        if isinstance(item, dict)
        and item.get("role") == "user"
        and isinstance(item.get("content"), str)
        and item["content"].strip()
    ][-4:]
    try:
        answer = await llm_service.chat(
            recent_user_history + [{"role": "user", "content": question}],
            context=build_context_block(hits), max_new_tokens=600,
        )
    except LLMUnavailable:
        return {"answer": "[ANSWER UNAVAILABLE] The configured language model is temporarily unavailable. No legal answer is being presented.", "sources": [], "analysis_status": "unavailable_model"}
    if not isinstance(answer, str) or not answer.strip():
        return {"answer": "[ANSWER UNAVAILABLE] The language model returned no supported answer.", "sources": [], "analysis_status": "unavailable_model"}
    cited_indices = _validated_citation_indices(answer, len(hits))
    if cited_indices is None:
        return {"answer": "[ANSWER UNAVAILABLE] The language model did not return a verifiable reference to the supplied legal text.", "sources": [], "analysis_status": "unavailable_unsupported_answer"}
    return {"answer": answer, "sources": _citations([hits[index] for index in cited_indices]), "analysis_status": "available"}
