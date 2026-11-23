#!/bin/bash
cd /home/z/my-project/backend
source venv/bin/activate
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
