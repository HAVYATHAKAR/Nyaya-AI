#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-${BACKEND_PORT:-8000}}" --workers "${WEB_CONCURRENCY:-1}"
