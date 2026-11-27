# Backend and AI Reliability Implementation Plan

> **For agentic workers:** Steps use checkbox syntax for tracking.

**Goal:** Harden the existing FastAPI service and ensure its AI-facing responses distinguish real analysis from fallbacks.

**Architecture:** Retain the current FastAPI/SQLAlchemy API and SQLite/PostgreSQL support. Use safe server-generated upload paths, validate configuration at startup, and expose explicit analysis/service statuses in existing response fields. Disable unsupported hash-based retrieval rather than presenting it as semantic RAG.

**Tech Stack:** Python, FastAPI, Pydantic v2, SQLAlchemy, pytest, httpx.

**Spec:** `/home/ubuntu/upload/pasted_content.txt`

## Global Constraints

- Preserve product scope and API behavior where practical.
- Do not redesign the frontend or add infrastructure.
- Do not claim tests passed unless run.
- Do not commit API keys or secrets.

## Review Focus

- Oversized, empty, path-like, duplicate-name, or failed uploads must not leave unsafe files.
- User-controlled roles and cross-user document IDs must not grant privileges or access.
- Missing/failed AI and OCR must never appear as successful substantive analysis.
- Malformed model JSON and missing draft fields must be surfaced safely.
- Unsafe production JWT/CORS configuration must fail closed.

---

### Task 1: Runtime setup and secure configuration

**Files:** `backend/requirements.txt`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/api/auth.py`, `backend/app/api/schemas.py`, `backend/run.sh`, `backend/.env.example`.

- [x] Declare schema/runtime dependencies, validate strong JWT secret outside development, remove permissive credentialed CORS wildcard, and make run script portable.
- [x] Prevent client-selected signup roles; validate request bounds.
- [x] Test settings validation and role handling.

### Task 2: Upload and document ownership hardening

**Files:** `backend/app/api/documents.py`, `backend/app/api/schemas.py`, `backend/app/services/ocr_service.py`.

- [x] Stream upload in bounded chunks to a server-generated UUID path and clean partial files on all failures.
- [x] Preserve only sanitized original filename as display metadata; validate extension, empty files, and ownership.
- [x] Mark unreadable/stub OCR as failed/unavailable, not analyzed; avoid storing exception details containing sensitive content.
- [x] Test size limit, filename/path safety, cleanup, and cross-user access.

### Task 3: Truthful AI, retrieval, workflow, and drafts

**Files:** `backend/app/services/llm_service.py`, `backend/app/services/embed_service.py`, `backend/app/services/rag_service.py`, `backend/app/services/doc_intelligence.py`, `backend/app/services/workflow_generator.py`, `backend/app/services/draft_generator.py`, `backend/app/api/tools.py`, `backend/app/api/schemas.py`.

- [x] Return explicit availability metadata for LLM-backed outputs; constrain timeouts and safe logs.
- [x] Remove hash embeddings and disable retrieval/answer generation when a real embedding provider is not configured; retain source metadata and citation URLs for configured retrieval.
- [x] Validate structured model responses; label regex dates as text matches, not confirmed deadlines.
- [x] Validate workflow output and required draft fields; preserve preliminary disclaimer and escape template content.
- [x] Test unavailable services, malformed outputs, citations, invalid workflows, and missing draft inputs.

### Task 4: Documentation and verification

**Files:** `README.md`, `backend/tests/*`.

- [x] Correct feature/setup claims and document required variables, OCR/PDF support, retrieval configuration, and migration caveat.
- [x] Run focused tests, full backend tests, compile check, and report exact outcomes plus remaining risks.
