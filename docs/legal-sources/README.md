# Legal source registry and ingestion

Legal Q&A is **disabled by default**. The registry contains three discovered India Code Acts but marks all of them `pending`; a URL and an official government host do not establish currentness or legal review. The source PDFs identify their text as “As on the 6th October, 2025.” A qualified human reviewer must verify the exact text, amendments and commencement scope, then record a review date and SHA-256 hash of the exact PDF reviewed before ingestion can run.

## Sources currently discovered

The records are the Bharatiya Nyaya Sanhita, 2023 (Act 45), Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46), and Bharatiya Sakshya Adhiniyam, 2023 (Act 47). Official record URLs, bitstream URLs, section counts, and observations are recorded in [`research-notes.md`](research-notes.md). All point to India Code's official `indiacode.gov.in` host. Their displayed section totals are 358, 531, and 170 respectively. The official attached text carries an as-on date of 2025-10-06. Later changes are not verified here.

The registry records the commencement date shown in the official attached documents (1 July 2024) and preserves the disclosed exceptions/scope in `effective_date_scope`. This is source metadata, not a legal opinion about application to a particular matter. Enactment date is not used as an effective date.

## Review and registry update process

Before a source is made retrievable, a reviewer must inspect the official record and exact attached file, check amendments/notifications and any section-specific commencement, assess version currency, and assess extraction quality. They then update the source entry in `registry.json`:

- `review_status`: `reviewed` only after that review; otherwise keep `pending` or mark `rejected`.
- `reviewed_at`: ISO `YYYY-MM-DD`, the actual human review date.
- `retrieved_at`: ISO-8601 timestamp of the exact source-file download.
- `content_hash`: lowercase SHA-256 of the exact binary PDF reviewed.
- `document_version_date`: date printed in the official consolidated file, when present.
- `effective_date` and `effective_date_scope`: only if supported by the official text/notification; otherwise use `null` and explain unknown/partial scope.

The ingestion service rejects unapproved URLs, redirects, non-PDF responses, oversized downloads, unsupported content and any PDF whose current hash differs from the reviewed registry hash. A content update requires a new human review and a new pinned hash. Ingestion never marks a source reviewed automatically.

## Local setup and ingestion

Install the backend and optional real retrieval dependencies:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-embeddings.txt
```

Set `EMBEDDING_ENABLED=true` and a real `EMBED_MODEL`. In development/test, Qdrant local persistent mode stores files under `QDRANT_LOCAL_PATH` (default `./data/qdrant`). Keep this directory on persistent storage and back it up appropriately. Production requires a configured Qdrant server URL and API key; production never falls back to local disk or process memory. The Qdrant collection dimension must match the configured model. `QDRANT_COLLECTION` selects the collection.

After a reviewer has updated the registry, run from `backend/`:

```bash
python scripts/ingest_legal_sources.py
# or limit to reviewed sources:
python scripts/ingest_legal_sources.py --source-id india-bns-2023
```

The index is written with deterministic chunk IDs. Re-running an unchanged source is repeatable. No legal source is fetched or indexed at server startup. A missing model, Qdrant, source review, pinned hash, valid section extraction, or dimension match fails closed.

## Availability and limitations

`GET /api/chat/status` returns a structured readiness state. An empty, missing, unreviewed, stale or incompatible index disables answers. Retrieval requires India jurisdiction, an allowlisted official URL, a reviewed registry entry, a matching source hash, a section identifier, a review date within `LEGAL_SOURCE_MAX_REVIEW_AGE_DAYS` (default 180), and a relevance threshold. Answers require an explicit reference marker and return structured citations with title, law, section, official URL, jurisdiction, review date, and effective date when available.

Retrieved statute text is passed as untrusted evidence, not prompt instructions. The model is instructed to use supplied text only; answers that have no valid reference marker abstain. This is a grounding safeguard, not a guarantee that generative output is legally correct. Review every source before use and have users consult a qualified advocate.
