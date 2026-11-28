"""Application configuration loaded from environment variables."""
import json
import math
import os
from pathlib import Path
from typing import List

from pydantic import field_validator, model_validator
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

    # Database — SQLite for local development; PostgreSQL via psycopg in production.
    database_url: str = "sqlite:///./data/db/nyayaai.db"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = "postgresql+psycopg://" + value[len("postgres://"):]
        elif value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        if not (value.startswith("sqlite:") or value.startswith("postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use sqlite or PostgreSQL with psycopg")
        return value

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
    embedding_enabled: bool = False

    # Qdrant
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "nyayaai_legal_kb"
    qdrant_local_path: str = "./data/qdrant"
    legal_source_max_review_age_days: int = 180

    # Storage
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 20

    @model_validator(mode="after")
    def validate_security_settings(self):
        origins = self.cors_origins_list
        if not origins or not all(isinstance(origin, str) and origin.strip() for origin in origins):
            raise ValueError("CORS_ORIGINS must be a non-empty JSON array of explicit origins")
        if self.app_env.lower() not in {"development", "dev", "test"}:
            known_placeholders = ("change_me", "dev-only", "your_secret", "secret_key")
            frequencies = {char: self.jwt_secret.count(char) / max(1, len(self.jwt_secret)) for char in set(self.jwt_secret)}
            estimated_entropy = -sum(p * math.log2(p) for p in frequencies.values()) * len(self.jwt_secret)
            if (len(self.jwt_secret) < 32 or estimated_entropy < 128 or
                    any(marker in self.jwt_secret.lower() for marker in known_placeholders)):
                raise ValueError("JWT_SECRET must be a high-entropy, non-placeholder secret of at least 32 characters outside development")
            if "*" in self.cors_origins_list:
                raise ValueError("CORS_ORIGINS cannot contain '*' outside development")
        if self.max_upload_mb < 1:
            raise ValueError("MAX_UPLOAD_MB must be at least 1")
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            origins = json.loads(self.cors_origins)
            return origins if isinstance(origins, list) else []
        except Exception:
            return []

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

# Ensure data dirs exist
Path("./data/db").mkdir(parents=True, exist_ok=True)
Path("./data/uploads").mkdir(parents=True, exist_ok=True)
