"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .core.config import settings
from .db.session import init_db
from .api import auth, documents, chat, tools
from .services.rag_service import retrieval_status


class UploadLimitMiddleware:
    """Stop oversized upload bodies while ASGI is receiving them."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/documents/upload":
            await self.app(scope, receive, send)
            return
        max_bytes = settings.max_upload_mb * 1024 * 1024 + 256 * 1024
        headers = dict(scope.get("headers", []))
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            content_length = 0
        if content_length > max_bytes:
            await self._too_large(send)
            return
        received = 0
        response_started = False

        async def tracked_send(message):
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise ValueError("upload_body_too_large")
            return message

        try:
            await self.app(scope, limited_receive, tracked_send)
        except ValueError as exc:
            if str(exc) != "upload_body_too_large" or response_started:
                raise
            await self._too_large(send)

    @staticmethod
    async def _too_large(send):
        body = json.dumps({"detail": "Uploaded request exceeds the configured size limit"}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} backend...")
    init_db()
    # The legal corpus is never seeded from sample text or fetched at startup.
    # Reviewed sources are ingested explicitly with backend/scripts/ingest_legal_sources.py.
    logger.info("Startup complete.")
    yield
    # Shutdown
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Legal Intelligence & Workflow Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(UploadLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(tools.router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.1.0",
        "ocr_lang": settings.ocr_lang,
        "llm_model": settings.hf_model,
        "semantic_retrieval": retrieval_status(),
        "llm": "configured" if settings.hf_token else "unavailable_not_configured",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.app_debug,
    )
