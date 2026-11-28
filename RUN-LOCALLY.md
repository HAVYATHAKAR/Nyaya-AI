# NyayaAI — Run Locally (Windows + macOS/Linux)

> Set up in ~5 minutes. Works on PowerShell, CMD, bash, zsh.

---

## Prerequisites

Install these first if you don't have them:

- **Python 3.10+** → https://www.python.org/downloads/ (check "Add Python to PATH" on Windows)
- **Node.js 18+** → https://nodejs.org/ (or `winget install OpenJS.NodeJS` on Windows)
- **Bun** (optional, faster than npm) → https://bun.sh/

Verify:
```powershell
python --version    # should be 3.10+
node --version      # should be 18+
```

---

## 1. Backend setup

### Windows (PowerShell)

```powershell
# Navigate to the unzipped folder (the one containing README.md, backend/, src/)
cd C:\path\to\nyayaai-source
cd backend

# Create virtualenv
python -m venv venv

# Activate — Windows uses .\ not source
.\venv\Scripts\Activate.ps1

# If you get "running scripts is disabled" error, run this once:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# Then retry activation.

# Install deps
pip install -r requirements.txt

# Copy env file
Copy-Item .env.example .env

# Run the backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### macOS / Linux (bash/zsh)

```bash
cd /path/to/nyayaai-source/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Expected output

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Open http://localhost:8000/docs — if you see the Swagger UI, the backend is working. ✅

---

## 2. Frontend setup

Open a **second terminal** (keep the backend running in the first one).

### Windows (PowerShell)

```powershell
cd C:\path\to\nyayaai-source

# Install deps
npm install
# OR if you have bun: bun install

# The Next.js dev server proxies same-origin /api requests to 127.0.0.1:8000.
# Override API_PROXY_TARGET if your backend is on a different host/port.

# Run dev server
npm run dev
# OR: bun run dev
```

### macOS / Linux

```bash
cd /path/to/nyayaai-source
npm install   # or: bun install
npm run dev   # or: bun run dev
```

Browser requests use relative `/api/...` paths. Next.js proxies those paths to the local FastAPI server during development. For a different backend, start Next.js with `API_PROXY_TARGET=http://127.0.0.1:8000` (set with `$env:API_PROXY_TARGET` in PowerShell). For a deployed frontend, configure the platform reverse proxy to route `/api/*` to FastAPI, or set `NEXT_PUBLIC_BACKEND_URL` to a browser-reachable HTTPS backend origin.

### Expected output

Open http://localhost:3000 → you'll see the NyayaAI login page.

---

## 3. Try it

1. Click **"Create Account"** tab
2. Enter any email (e.g. `you@example.com`) + password (min 6 chars)
3. No demo account is seeded; create a new account instead.

You'll see 4 tabs:
- **Documents** — upload supported files; OCR/model analysis depends on configured runtime services and reports unavailable failures
- **AI Assistant** — Q&A remains unavailable until a reviewed URL-cited legal corpus and real retrieval pipeline are integrated
- **Workflow** — describe your case, get a step-by-step plan
- **Drafts** — generate RTI / Consumer Complaint / Legal Notice / Affidavit / Rental Agreement

---

## 4. (Optional) Enable real AI

### Live LLM via HuggingFace (free)

1. Sign up at https://huggingface.co
2. Profile → Settings → **Access Tokens** → Create new token (type: Read, free)
3. Edit `backend/.env`:
   ```
   HF_TOKEN=hf_your_token_here
   HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
   ```
4. Stop the backend (Ctrl+C) and restart it. Model-backed workflows/document analysis can then call the configured provider; legal Q&A remains disabled without a verified source corpus.

### Real OCR (optional, ~500 MB)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements-ocr.txt
```

Edit `backend/.env`:
```
OCR_LANG=hi    # or: en, ta, te, mr, bn, gu, pa, kn
```

### Legal Q&A / retrieval status

Legal Q&A is disabled by default: the three discovered India Code Acts are marked pending human review in `docs/legal-sources/registry.json`. Their official files state “as on 6 October 2025,” so later amendments have not been verified by this repository. Do not mark an entry reviewed unless the exact file, amendments and commencement scope have been checked by a qualified reviewer.

Install the optional persistent retrieval stack from `backend/` with `pip install -r requirements-embeddings.txt`. Development/test use Qdrant local disk at `QDRANT_LOCAL_PATH` (default `./data/qdrant`); production requires `QDRANT_URL` and `QDRANT_API_KEY`. Set `EMBEDDING_ENABLED=true` and `EMBED_MODEL` to load real sentence-transformer embeddings. Update the reviewed registry entry with a human review date and the exact PDF SHA-256, then run `python scripts/ingest_legal_sources.py`. Only India Code HTTPS bitstream endpoints are allowed; changed content requires new review and hash pinning. Details: `docs/legal-sources/README.md`. `GET /api/chat/status` reports the current gate state. A configured vector store alone does not enable Q&A.

---

## Common Issues & Fixes

### 1. `Set-ExecutionPolicy` error on Windows PowerShell

```
.\venv\Scripts\Activate.ps1 : File cannot be loaded because running scripts is
disabled on this system.
```

**Fix:** Run this once, then retry:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 2. `pip install` fails on a specific package (e.g. `huggingface_hub==0.26.8`)

Pinned versions sometimes don't exist for all platforms. The shipped
`requirements.txt` now uses `>=` for cross-platform compatibility. If you
have an old copy, re-download the zip or edit `requirements.txt` and
remove the `==` pins.

### 3. `python` command not found on Windows

You forgot to check "Add Python to PATH" during install. Fix:
```powershell
# Either reinstall Python with the checkbox, OR:
$env:Path += ";C:\Users\Havya Thakar\AppData\Local\Programs\Python\Python312"
$env:Path += ";C:\Users\Havya Thakar\AppData\Local\Programs\Python\Python312\Scripts"
```

### 4. Backend crashes with `ModuleNotFoundError: No module named 'loguru'`

You skipped `pip install -r requirements.txt` (or it failed halfway).
Re-run it after activating the venv:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5. Frontend shows `fetch failed` / `Network Error`

Confirm FastAPI is listening on port 8000 and that Next.js started with
`API_PROXY_TARGET=http://127.0.0.1:8000` if the backend is not at its default
address. Browser calls use same-origin `/api/...` URLs and are proxied by
Next.js in development.

### 6. `bcrypt password cannot be longer than 72 bytes`

Already fixed in `app/core/security.py` (truncates to 72 bytes). If you
see this error, you're running an old version of the code — re-download
the zip.

### 7. Port 8000 already in use

Something else is using port 8000. Either kill that process, or use a
different port:
```powershell
python -m uvicorn app.main:app --port 8001 --reload
# Start Next with API_PROXY_TARGET=http://127.0.0.1:8001
```

### 8. CORS errors in browser console

The backend already allows `*` origins in dev. If you still see CORS
errors, check the backend terminal — there's usually a more specific
error printed (like a 500 from a real bug).

---

## Verify it works

Run this in a third terminal (after both backend + frontend are running):

```powershell
# Backend health
curl http://localhost:8000/api/health
# Expected: {"status":"ok","app":"NyayaAI","version":"0.1.0",...}

# Frontend
curl http://localhost:3000
# Expected: HTML page (200 OK)
```

If both succeed, open http://localhost:3000 in your browser and log in.

---

## Still stuck?

Send me:
1. The exact command you ran
2. The full error output (copy-paste, don't truncate)
3. Output of `python --version` and `node --version`
4. OS (Windows version / macOS version / Linux distro)

I'll fix it immediately.
