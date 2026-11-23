"""Application configuration loaded from environment variables."""
import json
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "NyayaAI"
    app_env: str = "development"
    app_debug: bool = True
    backend_port: int = 8000

    # Database — sandbox may pollute DATABASE_URL with a non-SQLAlchemy format.
    # We force our own URL by ignoring the env var unless it parses cleanly.
    database_url: str = "sqlite:///./data/db/nyayaai.db"

    # JWT
    jwt_secret: str = "change_me_in_production_please_use_a_long_random_string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # CORS — accept as JSON string in env
    cors_origins: str = '["http://localhost:3000"]'

    # OCR
    ocr_lang: str = "en"
    ocr_use_gpu: bool = False

    # HuggingFace
    hf_token: str = ""
    hf_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    # Embeddings
    embed_model: str = "BAAI/bge-small-en-v1.5"

    # Qdrant
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "nyayaai_legal_kb"

    # Storage
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 20

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.cors_origins)
        except Exception:
            return ["http://localhost:3000"]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

# If sandbox injected a bad DATABASE_URL (not SQLite/Postgres format), override it.
_url = settings.database_url
if not (_url.startswith("sqlite") or _url.startswith("postgres")):
    settings.database_url = "sqlite:///./data/db/nyayaai.db"

# Ensure data dirs exist
Path("./data/db").mkdir(parents=True, exist_ok=True)
Path("./data/uploads").mkdir(parents=True, exist_ok=True)
