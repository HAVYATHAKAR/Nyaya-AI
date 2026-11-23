# NyayaAI — AI-Powered Legal Intelligence & Workflow Platform

> Bridging citizens and justice through AI. An AI-powered platform that simplifies
> Indian legal documents, answers legal questions with source citations, generates
> personalized workflows, and drafts common legal documents.

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

1. **Document Intelligence** — Upload any legal doc (notices, FIRs, contracts, property papers). PaddleOCR extracts text, AI classifies the doc type, summarizes it, explains jargon in plain language, extracts deadlines and key entities, and flags missing information.

2. **AI Legal Assistant** — Ask natural-language legal questions ("How do I file an RTI?", "Which court handles consumer disputes?"). RAG retrieves verified legal context (RTI Act, Consumer Protection Act, IPC, etc.) and grounds every answer with source citations.

3. **Workflow Generator** — Describe your situation and get a personalized step-by-step legal workflow with deadlines, priorities, a document checklist, and a "preparation score".

4. **Draft Generator** — Generate first drafts of common legal documents: RTI applications, consumer complaints, legal notices, affidavits, rental agreements. Each draft is watermarked as preliminary — review by an advocate is mandatory.

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
│   Routes /api/*?XTransformPort=8000 → FastAPI :8000               │
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
                                │   - LLM (HuggingFace Inference)  │
                                │   - Embeddings (bge-small*)      │
                                │   - Vector store (Qdrant Cloud)   │
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
| OCR | PaddleOCR (multilingual) | Stub fallback for dev |
| LLM | HuggingFace Inference API (free tier) | Llama-3 / Mistral / Gemma |
| Embeddings | sentence-transformers + BAAI/bge-small-en-v1.5 | Hash-based fallback for dev |
| Vector DB | Qdrant Cloud (free tier) | In-memory fallback for dev |
| Drafts | Jinja2 templates | 5 templates shipped |
| DB | SQLite (dev) / PostgreSQL (prod) | Easy swap via env var |

---

## Modules Shipped (MVP v1)

### ✅ Module 1 — Document Intelligence
- Upload PDF / PNG / JPG / TXT up to 20 MB
- PaddleOCR extracts text (supports Indic scripts)
- AI classifies doc type (legal notice, FIR, contract, etc.)
- Generates summary, plain-language explanation
- Extracts deadlines (LLM + regex fallback)
- Identifies key entities (parties, amounts, sections, courts)
- Flags missing information
- Background async processing with status polling

### ✅ Module 2 — AI Legal Assistant (RAG)
- Chat interface with conversation history
- RAG retrieves from seeded KB (RTI Act, Consumer Protection Act, IPC, Easements Act, Rent Control, Industrial Disputes)
- Every answer includes source citations with title + source + snippet
- Conversational context (last 4 turns)
- Fallback stub answer when LLM is unreachable (so demo always works)

### ✅ Module 3 — Workflow Generator
- Free-text description → structured workflow
- Auto-detects case type or accepts hint
- Generates 4-6 step action plan with deadlines + priorities
- Personalized document checklist
- Preparation score (0-100)
- Fallback templates for property / consumer / RTI / generic

### ✅ Module 4 — Draft Generator
- 5 templates shipped: RTI Application, Consumer Complaint, Legal Notice, Affidavit, Rental Agreement
- Dynamic form fields per template
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
# Edit .env to set HF_TOKEN, QDRANT_URL, QDRANT_API_KEY (see below)

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
Or use the seeded demo account: `demo@nyayaai.in` / `demo123`.

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
| POST | `/api/chat/message` | Send message → AI answer |
| DELETE | `/api/chat/{id}` | Delete chat |
| POST | `/api/tools/workflow` | Generate workflow |
| GET | `/api/tools/drafts/templates` | List draft templates |
| POST | `/api/tools/drafts` | Generate draft |
| GET | `/api/tools/drafts` | List saved drafts |

---

## Configuration

Backend reads from `backend/.env`. Key settings:

```bash
# Required for live LLM answers (free at huggingface.co)
HF_TOKEN=hf_your_token_here
HF_MODEL=meta-llama/Meta-Llama-3-8B-Instruct

# Required for production RAG (free tier at qdrant.tech)
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=your_key_here

# Production database (SQLite works for dev)
DATABASE_URL=postgresql://user:pass@host:5432/nyayaai

# JWT secret — CHANGE THIS for production
JWT_SECRET=use_a_long_random_string

# OCR language
OCR_LANG=en  # hi, ta, te, mr, bn, gu, pa, kn also supported
```

Without these set, the app still runs in "demo mode" — RAG returns hash-based embeddings, LLM returns a stub answer, OCR returns the filename. This is intentional so judges can see the full pipeline even if external services are unavailable.

---

## Deployment

### Recommended: Render (free tier)

#### Backend (FastAPI on Render)
1. Push repo to GitHub
2. New Web Service on Render → connect repo
3. Build command: `pip install -r backend/requirements.txt`
4. Start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add env vars (HF_TOKEN, QDRANT_URL, etc.)
6. Add Postgres database (free tier) → set DATABASE_URL

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
│   │   │   ├── llm_service.py     # HuggingFace Inference API
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
