"""RAG service: retrieve relevant legal context, then answer with citations."""
from typing import List, Dict, Any, Optional
from loguru import logger

from .embed_service import embedding_service, vector_store
from .llm_service import llm_service


# Knowledge base of sample legal documents used during MVP
# (so the demo works without a full India Code ingestion pipeline).
SAMPLE_KB = [
    {
        "id": "rti_act_2005_sec_6",
        "title": "RTI Act 2005 — Section 6: Requesting Information",
        "source": "Right to Information Act, 2005",
        "text": (
            "Section 6 of the Right to Information Act, 2005 provides that a person who desires "
            "to obtain any information under this Act shall make a request in writing or through "
            "electronic means in English or Hindi or in the official language of the area in which "
            "the application is made, accompanying such fee as may be prescribed. The applicant "
            "need not give any reason for requesting the information. The Public Information "
            "Officer (PIO) must respond within 30 days of receipt of the application, or within "
            "48 hours if the information concerns the life or liberty of a person."
        ),
        "jurisdiction": "india",
    },
    {
        "id": "consumer_protection_2019_sec_35",
        "title": "Consumer Protection Act 2019 — Section 35: Complaint Procedure",
        "source": "Consumer Protection Act, 2019",
        "text": (
            "Section 35 of the Consumer Protection Act, 2019 governs the procedure for filing "
            "a consumer complaint. A complaint may be filed before the District Consumer Disputes "
            "Redressal Commission if the value of goods/services paid does not exceed Rs. 50 lakh, "
            "before the State Commission if it exceeds Rs. 50 lakh but not Rs. 2 crore, and before "
            "the National Commission if it exceeds Rs. 2 crore. The complaint must be filed within "
            "two years from the date on which the cause of action arose."
        ),
        "jurisdiction": "india",
    },
    {
        "id": "ipc_415_cheating",
        "title": "Indian Penal Code — Section 415: Cheating",
        "source": "Indian Penal Code, 1860",
        "text": (
            "Section 415 IPC defines cheating: A person is said to 'cheat' when, by deceiving "
            "any person, fraudulently or dishonestly induces the person so deceived to deliver "
            "any property to any person, or to consent that any person shall retain any property, "
            "or intentionally induces the person so deceived to do or omit to do anything which "
            "he would not do or omit if he were not so deceived. Punishment under Section 417 is "
            "imprisonment up to 1 year, or fine, or both."
        ),
        "jurisdiction": "india",
    },
    {
        "id": "rent_control_delhi_1958",
        "title": "Delhi Rent Control Act 1958 — Landlord & Tenant Rights",
        "source": "Delhi Rent Control Act, 1958",
        "text": (
            "Under the Delhi Rent Control Act, 1958, a landlord cannot evict a tenant without a "
            "valid ground specified under Section 14, such as non-payment of rent, sub-letting "
            "without permission, or the landlord bona fide requiring the premises for personal "
            "use. Rent increases are limited to the rates prescribed under the Act. For tenancies "
            "outside the Act (high-rent premises), the terms of the rental agreement prevail, "
            "but the landlord must give at least 15 days' written notice before termination."
        ),
        "jurisdiction": "delhi",
    },
    {
        "id": "indian_easements_1882",
        "title": "Indian Easements Act 1882 — Property Rights",
        "source": "Indian Easements Act, 1882",
        "text": (
            "The Indian Easements Act, 1882 defines the rights of property owners, including "
            "the right to quiet enjoyment, the right to exclude others, and easements such as "
            "right of way. Disputes over property boundaries, easements, and adverse possession "
            "are governed by this Act and the Limitation Act, 1963. Civil suits for property "
            "recovery must be filed within 12 years from the date the cause of action arises."
        ),
        "jurisdiction": "india",
    },
    {
        "id": "labour_code_2020_industrial_disputes",
        "title": "Industrial Disputes Act 1947 — Section 2A: Termination Disputes",
        "source": "Industrial Disputes Act, 1947",
        "text": (
            "Under Section 2A of the Industrial Disputes Act, 1947, a workman who has been "
            "discharged, dismissed, retrenched, or whose services have been otherwise terminated "
            "may raise an industrial dispute directly with the Labour Court or Tribunal. The "
            "dispute must be raised within 3 years of the termination. The employer must prove "
            "that the termination was for a valid reason and followed due process, including "
            "holding an inquiry and giving the workman an opportunity to be heard."
        ),
        "jurisdiction": "india",
    },
]


CHUNK_SIZE = 500  # chars
CHUNK_OVERLAP = 100


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
    logger.info("Seeding knowledge base...")
    chunks = []
    for doc in SAMPLE_KB:
        # Each KB doc is short enough to be a single chunk
        chunks.append({
            "id": doc["id"],
            "text": doc["text"],
            "source": doc["source"],
            "title": doc["title"],
            "jurisdiction": doc.get("jurisdiction", "india"),
        })
    if not chunks:
        return
    embeddings = embedding_service.encode([c["text"] for c in chunks])
    vector_store.upsert(chunks, embeddings)
    logger.info(f"Seeded {len(chunks)} knowledge-base chunks.")


async def retrieve_context(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Retrieve top_k relevant chunks for the query."""
    q_emb = embedding_service.encode_one(query)
    return vector_store.search(q_emb, top_k=top_k)


def build_context_block(hits: List[Dict[str, Any]]) -> str:
    """Render retrieved chunks into a context block for the LLM."""
    if not hits:
        return ""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(
            f"[{i}] Source: {h.get('title', 'Unknown')}\n"
            f"Reference: {h.get('source', 'Unknown')}\n"
            f"Content: {h.get('text', '')}\n"
        )
    return "\n---\n".join(parts)


async def answer_question(
    question: str, history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """End-to-end RAG: retrieve → prompt → answer."""
    hits = await retrieve_context(question, top_k=4)
    context = build_context_block(hits)

    messages = []
    if history:
        # Last 4 turns for context
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": question})

    answer = await llm_service.chat(messages, context=context, max_new_tokens=600)

    sources = [
        {
            "title": h.get("title", ""),
            "source": h.get("source", ""),
            "snippet": h.get("text", "")[:300],
            "score": h.get("score", 0),
        }
        for h in hits
    ]
    return {"answer": answer, "sources": sources}
