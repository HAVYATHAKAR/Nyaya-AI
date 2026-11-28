"""Allowlisted, metadata-validated ingestion of reviewed official legal sources."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "docs" / "legal-sources" / "registry.json"
ALLOWED_HOSTS = {"indiacode.gov.in"}
ALLOWED_PATH_PREFIXES = ("/server/api/core/bitstreams/",)
MAX_SOURCE_BYTES = 32 * 1024 * 1024
HTTP_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


class LegalSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9][a-z0-9._-]+$")
    title: str = Field(min_length=3, max_length=300)
    jurisdiction: str = Field(min_length=2, max_length=100)
    law_id: str = Field(min_length=3, max_length=150)
    official_url: HttpUrl
    effective_date: date | None = None
    effective_date_scope: str | None = None
    retrieved_at: datetime | None = None
    reviewed_at: date | None = None
    review_status: str = Field(pattern=r"^(pending|reviewed|rejected)$")
    content_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    document_version_date: date | None = None

    @field_validator("jurisdiction")
    @classmethod
    def jurisdiction_is_canonical(cls, value: str) -> str:
        if value != "India":
            raise ValueError("Only explicitly supported jurisdiction 'India' is accepted")
        return value

    @model_validator(mode="after")
    def validate_review_state(self):
        if self.review_status == "reviewed" and (self.reviewed_at is None or self.content_hash is None or self.retrieved_at is None):
            raise ValueError("reviewed sources require reviewed_at, retrieved_at, and a pinned content_hash")
        if self.review_status != "reviewed" and self.reviewed_at is not None:
            raise ValueError("only reviewed sources may have reviewed_at")
        parsed = urlparse(str(self.official_url))
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("source URL must use HTTPS on an explicitly allowlisted host")
        if not any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
            raise ValueError("source URL path is not an approved official document endpoint")
        if self.content_hash and self.retrieved_at is None:
            raise ValueError("content_hash requires retrieved_at")
        return self

    @property
    def is_reviewed(self) -> bool:
        return self.review_status == "reviewed" and self.reviewed_at is not None


def load_registry(path: Path | str = REGISTRY_PATH) -> list[LegalSource]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Legal source registry must be a JSON array")
    sources = [LegalSource.model_validate(item) for item in raw]
    ids = [source.source_id for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("Legal source registry contains duplicate source_id values")
    return sources


def validate_fetch_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Refusing source URL outside the HTTPS allowlist")
    if not any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES):
        raise ValueError("Refusing source URL outside approved document paths")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Refusing URL credentials or non-standard port")


async def fetch_pdf(source: LegalSource, client: httpx.AsyncClient | None = None) -> bytes:
    """Fetch only an approved PDF endpoint with bounded size/time and no redirects."""
    url = str(source.official_url)
    validate_fetch_url(url)
    owned = client is None
    client = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False)
    try:
        async with client.stream("GET", url, headers={"Accept": "application/pdf"}) as response:
            if response.is_redirect:
                raise ValueError("Official source redirected; refusing to follow unverified destination")
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/pdf":
                raise ValueError(f"Expected application/pdf, received {content_type or 'no content type'}")
            declared = response.headers.get("content-length")
            if declared and int(declared) > MAX_SOURCE_BYTES:
                raise ValueError("Official source exceeds the configured response-size limit")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_SOURCE_BYTES:
                    raise ValueError("Official source exceeds the configured response-size limit")
                chunks.append(chunk)
        body = b"".join(chunks)
        if not body.startswith(b"%PDF-"):
            raise ValueError("Official response did not contain a valid PDF header")
        return body
    finally:
        if owned:
            await client.aclose()


def extract_sections(pdf_bytes: bytes, source: LegalSource) -> list[dict[str, Any]]:
    """Extract section-oriented text; keep the longest occurrence per section (body over TOC)."""
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("Install requirements-embeddings.txt to extract official PDFs") from exc
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        text = "\n".join(page.get_text("text") for page in document)
    finally:
        document.close()
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    matches = list(re.finditer(r"(?m)^\s*(\d{1,3}[A-Za-z]?)\.\s+([^\n]+)", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start():end].strip()
        # Repeated section number entries occur in the table of contents and statute body.
        section = match.group(1)
        if len(body) >= 80 and len(body) > len(sections.get(section, "")):
            sections[section] = body
    if not sections:
        raise ValueError(f"No section-like legal text could be extracted for {source.source_id}")
    retrieved_at = datetime.now(timezone.utc)
    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    reviewed_at = source.reviewed_at.isoformat() if source.reviewed_at else None
    chunks: list[dict[str, Any]] = []
    for section, body in sorted(sections.items(), key=lambda pair: (int(re.match(r"\d+", pair[0]).group()), pair[0])):
        # A section can exceed embedding context; split without crossing section boundaries.
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", body) if part.strip()]
        current = ""
        part_number = 0
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > 1800:
                chunks.append(_make_chunk(source, section, part_number, current, content_hash, retrieved_at, reviewed_at))
                part_number += 1
                current = ""
            current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(_make_chunk(source, section, part_number, current, content_hash, retrieved_at, reviewed_at))
    return chunks


def _make_chunk(source: LegalSource, section: str, part: int, text: str,
                content_hash: str, retrieved_at: datetime, reviewed_at: str | None) -> dict[str, Any]:
    identity = f"{source.source_id}:{section}:{part}:{content_hash}"
    return {
        "id": str(uuid.UUID(hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32])),
        "text": text,
        "source_id": source.source_id,
        "title": source.title,
        "law_id": source.law_id,
        "section": section,
        "source": f"{source.law_id}, section {section}",
        "source_url": str(source.official_url),
        "jurisdiction": source.jurisdiction,
        "effective_date": source.effective_date.isoformat() if source.effective_date else None,
        "reviewed_at": reviewed_at,
        "review_status": source.review_status,
        "retrieved_at": retrieved_at.isoformat(),
        "document_version_date": source.document_version_date.isoformat() if source.document_version_date else None,
        "content_hash": content_hash,
    }


async def ingest_sources(source_ids: set[str] | None = None) -> dict[str, Any]:
    """Fetch and persist reviewed sources. Pending sources are deliberately not indexed."""
    from .embed_service import embedding_service, vector_store

    sources = load_registry()
    selected = [s for s in sources if source_ids is None or s.source_id in source_ids]
    unknown = (source_ids or set()) - {s.source_id for s in sources}
    if unknown:
        raise ValueError(f"Unknown legal source IDs: {', '.join(sorted(unknown))}")
    reviewed = [s for s in selected if s.is_reviewed]
    if not reviewed:
        return {"status": "disabled_no_reviewed_sources", "indexed": 0, "skipped": len(selected)}
    if not embedding_service.available:
        raise RuntimeError("Real embedding model is unavailable; no legal sources were indexed")
    results = []
    for source in reviewed:
        body = await fetch_pdf(source)
        fetched_hash = hashlib.sha256(body).hexdigest()
        if source.content_hash != fetched_hash:
            raise ValueError(f"Official source content changed or is not pinned to the reviewed hash for {source.source_id}; human review is required")
        chunks = extract_sections(body, source)
        required = {"id", "text", "source_id", "title", "law_id", "section", "source_url",
                    "jurisdiction", "effective_date", "reviewed_at", "review_status", "retrieved_at",
                    "content_hash"}
        for chunk in chunks:
            if not required.issubset(chunk) or any(chunk.get(key) in (None, "") for key in required - {"effective_date"}):
                raise ValueError(f"Extracted passage is missing required audit metadata for {source.source_id}")
            if (chunk["source_id"] != source.source_id or chunk["title"] != source.title
                    or chunk["law_id"] != source.law_id or chunk["source_url"] != str(source.official_url)
                    or chunk["jurisdiction"] != source.jurisdiction
                    or chunk["reviewed_at"] != source.reviewed_at.isoformat()
                    or chunk["review_status"] != "reviewed"):
                raise ValueError(f"Extracted passage metadata does not match registry source {source.source_id}")
        vectors = embedding_service.encode([chunk["text"] for chunk in chunks])
        if not vectors or any(not vector for vector in vectors):
            raise RuntimeError(f"Embedding model returned empty vectors for {source.source_id}")
        vector_store.upsert(chunks, vectors)
        results.append({"source_id": source.source_id, "chunks": len(chunks), "content_hash": hashlib.sha256(body).hexdigest()})
    return {"status": "indexed", "indexed": sum(item["chunks"] for item in results), "sources": results}
