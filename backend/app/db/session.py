"""SQLAlchemy session + engine."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from ..core.config import settings


# SQLite needs check_same_thread=False for FastAPI
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Safe to call multiple times."""
    from . import models  # noqa: ensure models are imported
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("chat_messages")}
    if "analysis_status" not in columns:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE chat_messages ADD COLUMN analysis_status "
                "VARCHAR(50) NOT NULL DEFAULT 'not_applicable'"
            ))
            connection.execute(text(
                "UPDATE chat_messages SET analysis_status = CASE "
                "WHEN role = 'assistant' AND content LIKE '[ANSWER UNAVAILABLE]%' "
                "THEN 'unavailable_legacy' WHEN role = 'assistant' THEN 'available' "
                "ELSE 'not_applicable' END"
            ))
