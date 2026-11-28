# Verified Legal Q&A and Product Flow Reliability Implementation Plan

> **For agentic workers:** Implement task-by-task. The supplied user brief is the specification; changes must remain uncommitted and unpushed.

**Goal:** Enable legal Q&A only from verified, relevant, current official Indian legal texts, while validating actual website flows and OCR behavior.

**Architecture:** Add a declarative source registry and idempotent, allowlist-restricted ingestion service that validates source metadata and persists section-aware chunks and real embeddings in Qdrant. Keep Q&A fail-closed when source, review, embedding, storage, or model evidence is insufficient. Make UI answer state and official citations explicit; validate drafts remain plain text. Verify local flows in a browser and evaluate OCR on synthetic English/Hindi image and scanned-PDF fixtures.

**Tech Stack:** Existing FastAPI/SQLAlchemy, Next.js 16/React, Qdrant, sentence-transformers, pytest, npm/Next tooling, PaddleOCR, pdf2image/Poppler.

**Spec:** `/home/ubuntu/upload/pasted_content_2.txt`

## Global Constraints

- Use authoritative Indian government or official legal sources only; do not invent legal text or correction.
- Require official URL, jurisdiction, law/section, retrieval/review metadata, content hash, and effective date only when verified/available.
- Restrict ingestion to explicitly allowlisted official domains, with timeouts, response-size and content-type limits.
- Preserve section identity and source citation metadata on every chunk.
- Retrieval stays disabled for missing, empty, stale, invalid, or incompatible indexes; retrieved text is untrusted reference, not instructions.
- Do not commit or push changes; do not include private legal documents or personal data.
- Do not claim website functionality or OCR accuracy without exercising real flows and real sample files.

## Review Focus

- An official URL can still lead to an amended, superseded, empty, or malformed source; ingestion must validate review state and content hash.
- Matching embeddings with no jurisdiction/review metadata must never enable Q&A.
- Similarity scores alone can rank irrelevant legal text; use evaluated acceptance cases and abstention tests.
- Source text may contain prompt-injection instructions; model output must remain grounded and citation-linked.
- Ingestion retries, changed source content, model dimension drift, or partial failures must not leave a falsely healthy index.

---

### Task 1: Verify current main and source records

**Files:** `docs/legal-sources/registry.json`, `docs/superpowers/plans/2026-11-27-verified-legal-rag.md`.

- [ ] Confirm current `origin/main` already contains the prior reliability changes; do not repeat them.
- [ ] Verify each selected Act's official India Code record and content directly; include only reviewed sources and accurately record unknown effective dates as null.
- [ ] Record source URLs and observed metadata in project documentation.

### Task 2: Source registry and ingestion

**Files:** create `backend/app/services/legal_sources.py`, `backend/scripts/ingest_legal_sources.py`, registry JSON, and focused tests.

- [ ] Validate source records and HTTPS allowlisted hosts before network access.
- [ ] Bound HTTP response size/time, check status and content type, and extract text from supported official HTML/PDF documents.
- [ ] Split by sections where possible; preserve title, act/section, jurisdiction, official URL, retrieval/review/effective dates, and SHA-256 content hash.
- [ ] Make ingestion idempotent and fail with an explicit status; never mark newly fetched material reviewed automatically.

### Task 3: Persistent vector storage and grounded retrieval

**Files:** `backend/app/services/embed_service.py`, `backend/app/services/rag_service.py`, config, optional dependency declarations, tests.

- [ ] Replace process-memory storage with persistent Qdrant local-path mode for development and configured Qdrant server mode for production.
- [ ] Validate model/index dimensions and readiness; reject missing credentials, empty indexes, stale sources, and model/storage failures.
- [ ] Filter by jurisdiction and source review metadata; adopt a relevance threshold only after tests against representative relevant and irrelevant questions.
- [ ] Require answer citations with title, section, official URL, jurisdiction, and review date; abstain if generation lacks reference support.
- [ ] Treat retrieved text as data with explicit anti-instruction prompt handling; tests include prompt-injection-like source text.

### Task 4: Chat UI, citation display, and plain-text drafts

**Files:** `backend/app/api/schemas.py`, `src/lib/api.ts`, `src/app/page.tsx`, `backend/app/services/draft_generator.py`, tests.

- [ ] Return structured status independently of answer-string parsing and persist/serialize it with chat messages.
- [ ] Show unavailable/insufficient-source/model states and render official citation links with section and review date.
- [ ] Remove nonexistent demo login and misleading sample prompt copy.
- [ ] Remove HTML entity encoding from plain-text draft generation while preserving safe React text rendering.

### Task 5: Actual local website flows

**Files:** frontend/backend test coverage and setup docs as needed.

- [ ] Run documented local services and test signup, login, session restore, logout, upload/status, document errors/results, chat unavailability/citations, workflow fallback, and draft generate/save/open/copy/download.
- [ ] Check configured proxy routing, browser console, failed requests, and fix flow-blocking defects only.

### Task 6: Real OCR evaluation

**Files:** `backend/tests/fixtures/ocr/`, OCR tests and setup docs.

- [ ] Install optional OCR and PDF dependencies in the sandbox; generate small non-sensitive English and Hindi text image fixtures plus a scanned PDF with known ground truth.
- [ ] Run extraction and compare normalized character/word error rate; report sample creation and exact metric.
- [ ] Verify unsupported, unreadable, missing-dependency, and OCR failure paths remain failed/unavailable rather than fabricated.

### Task 7: Documentation and final verification

**Files:** `README.md`, `RUN-LOCALLY.md`, relevant source registry guide.

- [ ] Document exactly which legal sources are included, source review state, ingestion command, Qdrant modes/tradeoffs, and enablement requirements.
- [ ] Run backend tests, relevant frontend checks, and browser/OCR checks; report exact outcomes and remaining blockers.
- [ ] Confirm working tree changes remain uncommitted and unpushed.
