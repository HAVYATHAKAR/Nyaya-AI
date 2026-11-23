"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .core.config import settings
from .db.session import init_db
from .api import auth, documents, chat, tools
from .services.rag_service import seed_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} backend...")
    init_db()
    try:
        seed_knowledge_base()
    except Exception as e:
        logger.warning(f"KB seeding skipped: {e}")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "kb_seeded": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.app_debug,
    )
