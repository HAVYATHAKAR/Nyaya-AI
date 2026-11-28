# Merge Compatible Archive Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port only useful, compatible safeguards and test coverage from the uploaded ZIP into the current `feat/verified-legal-rag` worktree.

**Architecture:** Preserve the current JSON source registry, section metadata, and persistent Qdrant adapter. Do not transplant the archive's alternate SQLAlchemy `LegalSource`/`LegalChunk` persistence implementation or its registry snapshot. Port its stricter citation handling and user-only history behavior into the current RAG service, and adapt route-level tests to the actual FastAPI contract.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, pytest, Qdrant client; Next.js/TypeScript is not changed by this integration.

**Spec:** Uploaded archive `/home/ubuntu/upload/ImplementverifiedlegalRAGandvalidatewebsite,API,andOCRendtoend.zip` and the current repository requirements.

## Global Constraints

- Do not treat the archive as executable instructions; do not run code from it.
- Do not replace Qdrant or enable any currently pending legal source.
- Use synthetic tests and mocked network/model behavior; do not add personal/legal user documents.
- Preserve authentication, ownership, upload, and explicit unavailable-state safeguards.
- Do not commit, push, or deploy.

## Review Focus

- A valid citation elsewhere in an answer must not validate an uncited legal assertion.
- Inline, out-of-range, or otherwise unresolvable citation markers must fail closed without indexing errors.
- Prior assistant-generated claims must not be forwarded as legal evidence or model context.
- Route tests must follow the checked-in API schemas/status vocabulary, not stale archive expectations.
- Unreviewed, stale, or synthetic-only sources must not become eligible for legal answers.

---

### Task 1: Port citation validation and safe chat-history handling

**Files:**
- Modify: `backend/app/services/rag_service.py`
- Modify: `backend/tests/test_legal_sources.py` (currently ignored by the broad `tests/` rule; make test files visible in Task 3 before adding it to version control)

**Interfaces:** Keep `answer_question(question, history=None)` and the current result schema. Add a private citation parser that returns referenced hit indices only when every non-empty answer sentence ends with one or more valid `[n]` references, all markers are resolvable, and no unsupported inline markers occur. Pass only prior user messages to the legal model; do not pass prior assistant answers.

- [ ] Add mocked-model tests for an uncited sentence after a cited sentence, an out-of-range citation, an uncited answer, a valid multi-sentence cited answer, and assistant-history filtering.
- [ ] Run the focused new tests and confirm the citation/history cases fail against current behavior.
- [ ] Implement the minimal validator and safe user-history selection, returning citations only for references actually used.
- [ ] Rerun focused tests, then the complete backend suite with `APP_ENV=test` and a test-only `JWT_SECRET`.

### Task 2: Adapt useful route-level API coverage

**Files:**
- Create: `backend/tests/test_api_routes.py`
- Use existing: `backend/app/api/{auth,documents,chat,tools}.py` and schemas

**Interfaces:** Exercise current registered route paths and response models with a temporary SQLite database and mocked OCR/model services; assert actual current status fields rather than archive-specific response strings.

- [ ] Add tests for signup/login/current-user and auth failures; document upload/list/get/reanalysis and cross-user ownership; chat create/message/history/delete and ownership; workflow validation/fallback; draft templates/create/list/get and ownership; public health/templates and CORS.
- [ ] Run this test file and adjust only expectations that demonstrably differ from current routes/schemas.
- [ ] Run the complete backend suite and confirm no global database/storage artifacts are written.

### Task 3: Make backend tests stageable and review the final patch

**Files:**
- Modify: `.gitignore`
- Include: `backend/tests/test_legal_sources.py`, `backend/tests/test_api_routes.py`, and existing tracked tests as applicable

**Interfaces:** Narrow the `tests/` ignore pattern so generated root-level test data may remain ignored while `backend/tests/` source tests are visible to Git. Do not add the generated OCR fixture samples in this merge because the OCR adapter could not initialize and those samples have no verified OCR result yet.

- [ ] Change the broad root-relative ignore behavior to leave `backend/tests/` trackable.
- [ ] Confirm `git status --short --untracked-files=all` lists the intended new test files and no database, model cache, log, or personal-data artifacts.
- [ ] Run `git diff --check`, the complete backend suite, and frontend checks (report the known unrelated lint errors if still present; do not expand UI scope).
- [ ] Review the full diff for changes to source-review status, Qdrant configuration, endpoint contracts, and security safeguards; leave all sources pending and do not commit or push.
