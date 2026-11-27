"""RAG service: retrieve relevant legal context, then answer with citations."""
from typing import List, Dict, Any, Optional
from loguru import logger

from .embed_service import embedding_service, vector_store
from .llm_service import llm_service, LLMUnavailable


# Knowledge base of sample legal documents used during MVP
# (so the demo works without a full India Code ingestion pipeline).
# No seeded legal text is indexed until authoritative URLs and review dates are
# curated and verified. The historical IPC snippet is intentionally not served.
SAMPLE_KB = []

CHUNK_SIZE = 500  # chars
CHUNK_OVERLAP = 100
MIN_RELEVANCE_SCORE = 0.4


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple char-based chunker."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def seed_knowledge_base():
    """Pre-load the SAMPLE_KB into the vector store. Safe to call repeatedly."""
    if not embedding_service.available:
        logger.info("Semantic retrieval disabled; no knowledge base was indexed")
        return
    logger.info("Seeding verified legal knowledge base...")
    chunks = []
    for doc in SAMPLE_KB:
        # Each KB doc is short enough to be a single chunk
        chunks.append({
            "id": doc["id"],
            "text": doc["text"],
            "source": doc["source"],
            "title": doc["title"],
            "source_url": doc.get("source_url", ""),
            "jurisdiction": doc.get("jurisdiction", "india"),
            "reviewed_at": doc.get("reviewed_at", ""),
        })
    if not chunks:
        return
    embeddings = embedding_service.encode([c["text"] for c in chunks])
    vector_store.upsert(chunks, embeddings)
    logger.info(f"Seeded {len(chunks)} knowledge-base chunks.")


async def retrieve_context(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Retrieve top_k relevant chunks for the query."""
    if not embedding_service.available:
        return []
    q_emb = embedding_service.encode_one(query)
    # Require citable and recently reviewed source metadata before generation.
    return [
        hit for hit in vector_store.search(q_emb, top_k=top_k)
        if isinstance(hit.get("source_url"), str)
        and hit["source_url"].startswith("https://")
        and hit.get("jurisdiction")
        and hit.get("reviewed_at")
        and isinstance(hit.get("score"), (int, float))
        and float(hit.get("score", 0)) >= MIN_RELEVANCE_SCORE
    ]


def build_context_block(hits: List[Dict[str, Any]]) -> str:
    """Render retrieved chunks into a context block for the LLM."""
    if not hits:
        return ""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(
            f"[{i}] Source: {h.get('title', 'Unknown')}\n"
            f"Reference: {h.get('source', 'Unknown')}\n"
            f"URL: {h.get('source_url', '')}\n"
            f"Jurisdiction: {h.get('jurisdiction', 'Unknown')}\n"
            f"Reviewed: {h.get('reviewed_at', 'Unknown')}\n"
            f"Content: {h.get('text', '')}\n"
        )
    return "\n---\n".join(parts)


async def answer_question(
    question: str, history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """Answer only when configured semantic retrieval returns citable references."""
    try:
        hits = await retrieve_context(question, top_k=4)
    except Exception as exc:
        logger.warning("Legal retrieval unavailable ({})", type(exc).__name__)
        hits = []
    if not hits:
        return {
            "answer": "[ANSWER UNAVAILABLE] NyayaAI does not currently have sufficiently relevant, current legal source material to answer this question safely. Please consult an advocate or an authoritative legal source.",
            "sources": [],
            "analysis_status": "unavailable_insufficient_sources",
        }
    context = build_context_block(hits)
    messages = (history or [])[-4:] + [{"role": "user", "content": question}]
    try:
        answer = await llm_service.chat(messages, context=context, max_new_tokens=600)
        status = "available"
    except LLMUnavailable:
        answer = "[ANSWER UNAVAILABLE] The configured language model is temporarily unavailable. No generated legal answer is being presented."
        status = "unavailable_model"
    sources = [{"title": h.get("title", ""), "source": h.get("source", ""),
                "url": h.get("source_url", ""), "snippet": h.get("text", "")[:300],
                "jurisdiction": h.get("jurisdiction", ""),
                "reviewed_at": h.get("reviewed_at", ""),
                "score": h.get("score", 0)} for h in hits]
    return {"answer": answer, "sources": sources, "analysis_status": status}
