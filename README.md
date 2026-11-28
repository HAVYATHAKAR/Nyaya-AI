# NyayaAI — AI-Powered Legal Intelligence & Workflow Platform

> Legal document and workflow platform. Legal Q&A is disabled until official sources
> have a dated human review and are ingested into a persistent, citation-backed index.

![Status](https://img.shields.io/badge/status-MVP-yellow)
![Stack](https://img.shields.io/badge/stack-Next.js%20%2B%20FastAPI%20%2B%20Python-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Modules Shipped (MVP v1)](#modules-shipped-mvp-v1)
- [Quick Start (Local Dev)](#quick-start-local-dev)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

---

## Overview

**NyayaAI** transforms legal assistance from simple Q&A into an intelligent, structured, and workflow-driven experience. It is designed to help Indian citizens, legal professionals, businesses, NGOs, and government agencies simplify complex legal processes using AI.

The platform does NOT replace lawyers — it acts as an intelligent legal companion that prepares users *before* they approach a legal professional.

### What it does

1. **Document Intelligence** — Upload supported PDF/image/TXT files. OCR and model-backed analysis run only when their dependencies and services are available; failures are surfaced as unavailable/failed rather than fabricated summaries. Regex dates are explicitly uncertain text matches.

2. **AI Legal Assistant** — Q&A uses only relevant official legal references with review metadata. The India Code sources discovered so far are pending human review, so the default deployment reports Q&A unavailable. See [`docs/legal-sources/README.md`](docs/legal-sources/README.md).

3. **Workflow Generator** — The API returns validated model output when available, otherwise a clearly labeled template fallback; all timeframes are planning estimates, not legal deadlines.

4. **Draft Generator** — Render five plain-text templates. Missing fields remain explicit placeholders, original text values are preserved, and each draft carries a preliminary-only advocate-review disclaimer. The UI displays draft text as text, not HTML.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Browser (User)                            │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Caddy Reverse Proxy :81                       │
│   Routes /api/* → FastAPI :8000 (fixed upstream; client query cannot choose a port)               │
│   Routes everything else            → Next.js :3000               │
└──────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                            ▼
┌──────────────────────────┐   ┌──────────────────────────────────┐
│  Next.js Frontend :3000  │   │     FastAPI Backend :8000         │
│  (TypeScript + Tailwind) │   │     (Python)                      │
│                          │   │                                   │
│  - Login / Signup        │   │  /api/auth       — JWT + bcrypt    │
│  - Documents tab         │   │  /api/documents  — upload + OCR   │
│  - AI Assistant chat     │   │  /api/chat       — RAG Q&A        │
│  - Workflow generator    │   │  /api/tools      — workflow+draft │
│  - Draft generator       │   │                                   │
└──────────────────────────┘   │  Services:                        │
                                │   - OCR (PaddleOCR)              │
                                │   - LLM (HuggingFace Inference, optional token) │
│   - Real sentence-transformer embeddings (optional)          │
│   - Persistent Qdrant local/server vector store              │
                                │   - Drafts (Jinja2 templates)    │
                                │                                   │
                                │  Storage:                         │
                                │   - SQLite (dev) / Postgres       │
                                │   - Local FS (uploads)            │
                                └──────────────────────────────────┘
```

### Tech Stack

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, shadcn/ui | Single-page tabbed app |
| Backend | FastAPI (Python 3.12), SQLAlchemy, Pydantic v2 | Async, modular monolith |
| Auth | JWT (python-jose) + bcrypt | Email + password |
| OCR | PaddleOCR (optional `requirements-ocr.txt`) | No filename stub; reports unavailable |
| LLM | Hugging Face Inference Providers | OpenAI-compatible chat completions; model/provider availability depends on the configured account |
| Embeddings | Optional sentence-transformers (`requirements-embeddings.txt`) | Real vectors only |
| Vector store | Qdrant | Persistent local path in dev/test; server + API key in production; no RAM fallback |
| Drafts | Jinja2 templates | 5 templates shipped |
| DB | SQLite (dev) / PostgreSQL (prod) | Easy swap via env var |

---

## Backend capabilities and availability

### Document Intelligence
- Upload PDF / image / TXT up to the configured limit with streamed size checks and server-generated file paths
- OCR and model analysis require their runtime dependencies and services; failures are surfaced rather than fabricated
- Structured model responses are validated before saving
- Regex date matches are explicitly uncertain and are not declared legal deadlines
- OCR text remains available when OCR succeeds but model analysis is unavailable
- Background processing reports status through the document endpoint

### AI Legal Assistant (review-gated)
- Chat interface with conversation history
- Real embeddings and persistent Qdrant storage; no process-only index
- Ingestion is explicit and accepts only reviewed records from the India Code allowlist
- Source hashes are pinned at human review; changes invalidate ingestion/retrieval pending another review
- Retrieval checks jurisdiction, effective date when present, review freshness and relevance
- `/api/chat/status` and each chat response expose structured availability state; citations contain statute, section, official URL, jurisdiction and review date
- Unsupported or uncited model output is withheld; retrieved text is treated as untrusted reference data

### Workflow Generator
- Free-text description → structured workflow
- Auto-detects case type or accepts hint
- Validates model-generated step structure, values, and score bounds
- Fallback templates are returned with `analysis_status: template_fallback`
- Deadlines are labeled planning estimates, not legally binding dates

### Draft Generator
- 5 templates shipped: RTI Application, Consumer Complaint, Legal Notice, Affidavit, Rental Agreement
- Dynamic form fields per template
- Drafts are stored as plain text without HTML entity transformations; browser rendering uses text nodes
- Watermarked as "preliminary — review by advocate"
- Copy to clipboard + download as .txt
- Saved drafts list for re-use

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.10+
- Node.js 18+ / Bun
- ~2 GB disk space

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set HF_TOKEN and a strong production JWT_SECRET (see below)

# Start the backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be at `http://localhost:8000`. Swagger docs at `/docs`.

### 2. Frontend setup

```bash
# From project root
bun install  # or npm install
bun run dev  # or npm run dev
```

Frontend will be at `http://localhost:3000`.

### 3. Try the demo

Open `http://localhost:3000` and sign up with any email + password (min 6 chars).
No demo account is seeded by the backend; create a new account instead.

---

## API Documentation

Full interactive docs available at `http://localhost:8000/docs` once backend is running.

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/documents/upload` | Upload document (multipart) |
| GET | `/api/documents` | List user's documents |
| GET | `/api/documents/{id}` | Get document + AI analysis |
| POST | `/api/documents/{id}/reanalyze` | Re-run AI analysis |
| GET | `/api/chat` | List chats |
| POST | `/api/chat` | Create chat |
| GET | `/api/chat/{id}` | Get chat with messages |
| GET | `/api/chat/status` | Legal source/model/index availability |
| POST | `/api/chat/message` | Send message → grounded answer or explicit unavailable state |
| DELETE | `/api/chat/{id}` | Delete chat |
| POST | `/api/tools/workflow` | Generate workflow |
| GET | `/api/tools/drafts/templates` | List draft templates |
| POST | `/api/tools/drafts` | Generate draft |
| GET | `/api/tools/drafts` | List saved drafts |

---

## Configuration

Backend reads from `backend/.env`. Key settings:

```bash
# Required for live model-backed workflows and document analysis
HF_TOKEN=hf_your_token_here
HF_MODEL=meta-llama/Llama-3.1-8B-Instruct
HF_API_BASE_URL=https://router.huggingface.co/v1

# Optional real semantic retrieval; Q&A remains disabled until source review and ingestion
EMBEDDING_ENABLED=false
EMBED_MODEL=BAAI/bge-small-en-v1.5
QDRANT_COLLECTION=nyayaai_legal_kb
QDRANT_LOCAL_PATH=./data/qdrant  # dev/test persistent path
# Production: QDRANT_URL=https://... and QDRANT_API_KEY=...
LEGAL_SOURCE_MAX_REVIEW_AGE_DAYS=180

# Production database (SQLite works for dev)
DATABASE_URL=postgresql://user:pass@host:5432/nyayaai

# JWT secret — CHANGE THIS for production
JWT_SECRET=generate-a-unique-random-secret-at-least-32-characters

# OCR language
OCR_LANG=en  # hi, ta, te, mr, bn, gu, pa, kn also supported
```

For production, set `APP_ENV=production`, `APP_DEBUG=false`, a high-entropy `JWT_SECRET` (at least 32 characters), and `CORS_ORIGINS` to a JSON array of exact origins. Startup rejects weak production secrets, wildcard CORS, and debug mode. Without `HF_TOKEN`, model-backed workflows and document analysis are unavailable. AI uses the Hugging Face chat-completions router at `HF_API_BASE_URL`; choose an `HF_MODEL` that currently has an enabled Inference Provider for the account, and check any provider credits or billing requirements. OCR initialization failures and unreadable/empty OCR are reported as failed document processing; the filename is never treated as extracted text. Legal Q&A starts disabled because the registry sources are pending review. A qualified reviewer must pin the exact official PDF hash, review date and currentness before running the ingestion command described in [`docs/legal-sources/README.md`](docs/legal-sources/README.md). Local Qdrant data is persisted at `QDRANT_LOCAL_PATH`; production requires `QDRANT_URL` and `QDRANT_API_KEY` for legal retrieval. Without a reviewed corpus and persistent index, Q&A stays unavailable. The app does not fetch statutes at startup and never falls back to process memory. OCR packages are isolated in `backend/requirements-ocr.txt`; PDF OCR additionally requires system Poppler tools. Embeddings, Qdrant and PDF text extraction packages are isolated in `backend/requirements-embeddings.txt`.

---

## Deployment

### Recommended: Render (free tier)

#### Backend (FastAPI on Render)
1. Push repo to GitHub
2. New Web Service on Render → connect repo
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set `APP_ENV=production`, `APP_DEBUG=false`, a strong `JWT_SECRET`, and exact `CORS_ORIGINS`; set `HF_TOKEN` to enable model-backed workflows and document analysis
6. Add Postgres database (free tier) → set DATABASE_URL
7. For legal Q&A, install `backend/requirements-embeddings.txt`, configure production Qdrant (`QDRANT_URL` and `QDRANT_API_KEY`), then ingest only sources that have completed the review process. Q&A remains unavailable until this is complete.

#### Frontend (Next.js on Render or Vercel)
1. Push repo to GitHub
2. New Static Site on Render → connect repo
3. Build command: `bun install && bun run build`
4. Start command: `bun run start`
5. Set `NEXT_PUBLIC_API_URL` to backend Render URL

### Alternative: Railway / Fly.io / HuggingFace Spaces

The FastAPI backend deploys cleanly to any container host. The Next.js frontend
deploys to Vercel or any Next.js-compatible host.

---

## Project Structure

```
.
├── backend/                       # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint
│   │   ├── core/
│   │   │   ├── config.py          # Settings (env vars)
│   │   │   ├── security.py        # JWT + bcrypt
│   │   │   └── deps.py            # FastAPI dependencies
│   │   ├── db/
│   │   │   ├── session.py         # SQLAlchemy engine + session
│   │   │   └── models.py          # ORM models (User, Document, Chat, ...)
│   │   ├── api/
│   │   │   ├── auth.py            # /api/auth/*
│   │   │   ├── documents.py       # /api/documents/*
│   │   │   ├── chat.py            # /api/chat/*
│   │   │   ├── tools.py           # /api/tools/workflow + /drafts
│   │   │   └── schemas.py         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ocr_service.py     # PaddleOCR wrapper
│   │   │   ├── llm_service.py     # Hugging Face chat-completions client
│   │   │   ├── embed_service.py   # Embeddings + vector store
│   │   │   ├── rag_service.py     # RAG + KB seeding
│   │   │   ├── doc_intelligence.py
│   │   │   ├── workflow_generator.py
│   │   │   └── draft_generator.py
│   │   └── templates/             # Jinja2 draft templates
│   │       ├── rti_application.txt.j2
│   │       ├── consumer_complaint.txt.j2
│   │       ├── legal_notice.txt.j2
│   │       ├── affidavit.txt.j2
│   │       └── rental_agreement.txt.j2
│   ├── data/                      # SQLite + uploaded files (gitignored)
│   ├── requirements.txt
│   └── .env.example
├── mini-services/                 # Bun mini-service launcher
│   └── nyayaai-backend/
│       ├── index.ts                # Spawns Python uvicorn (detached)
│       └── package.json
├── src/                           # Next.js frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Main SPA (4 tabs)
│   │   └── globals.css
│   ├── components/ui/             # shadcn/ui components
│   └── lib/
│       ├── api.ts                 # Backend API client
│       └── utils.ts
├── package.json                   # Next.js deps
├── Caddyfile                      # Gateway config (port 81)
└── README.md                      # This file
```

---

## Roadmap

### v1 (shipped)
- ✅ Doc Intelligence (OCR + AI analysis)
- ✅ RAG Legal Assistant
- ✅ Workflow Generator
- ✅ Draft Generator (5 templates)
- ✅ JWT auth + email/password

### v2 (planned)
- ⬜ Case Companion workspace (timeline, evidence, witnesses, reminders)
- ⬜ Multilingual UI (Hindi, Tamil, Telugu, Marathi, Bengali, Gujarati, Punjabi, Kannada)
- ⬜ Voice input / TTS for accessibility
- ⬜ DigiLocker integration
- ⬜ eCourts API integration
- ⬜ Real PaddleOCR + bge-small embeddings in production
- ⬜ Specialized vertical modules (property, consumer, family, startup)

### v3 (vision)
- ⬜ Government API integration (GST, MCA, IT)
- ⬜ Compliance management for businesses
- ⬘ AI-assisted hearing preparation
- ⬘ Verified lawyer network + referral

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

### Code style
- Python: Black formatter, isort, type hints required
- TypeScript: ESLint + Prettier (configs included)
- Commit messages: conventional commits

---

## Disclaimer

NyayaAI is an **AI-powered legal assistance tool**, NOT a lawyer. Every output —
document analysis, chat answer, workflow, draft — is preliminary and must be
reviewed by a qualified advocate admitted to practice in India.

The platform does NOT:
- Provide independent legal advice
- Replace consultation with a licensed lawyer
- Guarantee legal outcomes
- Constitute an attorney-client relationship

The platform DOES:
- Help you understand legal documents in plain language
- Organize your case information
- Generate first drafts of common legal documents
- Cite the legal sources it draws from
- Prepare you for a more efficient consultation with a real advocate

For any legal matter, always consult a qualified legal professional.

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

## Acknowledgments

Built with these open-source tools:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [HuggingFace Hub](https://huggingface.co/)
- [Qdrant](https://qdrant.tech/)
- [sentence-transformers](https://www.sbert.net/)
- [shadcn/ui](https://ui.shadcn.com/)

Legal knowledge base content sourced from publicly available Indian legislation
(RTI Act 2005, Consumer Protection Act 2019, IPC 1860, Indian Easements Act 1882,
Delhi Rent Control Act 1958, Industrial Disputes Act 1947).
