"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Float, Boolean, JSON
)
from sqlalchemy.orm import relationship

from .session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="citizen")  # citizen | lawyer | ngo | business
    preferred_language = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)  # pdf, jpg, png
    file_size = Column(Integer, nullable=True)

    # OCR + AI analysis
    ocr_text = Column(Text, nullable=True)
    doc_type = Column(String, nullable=True)   # legal_notice, fir, contract, affidavit...
    summary = Column(Text, nullable=True)
    plain_explanation = Column(Text, nullable=True)
    deadlines = Column(JSON, nullable=True)        # list of {date, description}
    key_entities = Column(JSON, nullable=True)      # parties, amounts, sections
    missing_info = Column(JSON, nullable=True)      # list of missing fields

    status = Column(String, default="uploaded")  # uploaded|processing|analyzed|failed
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="documents")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "ChatMessage", back_populates="chat", cascade="all, delete-orphan"
    )
    user = relationship("User", back_populates="chats")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=_uuid)
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # list of {title, url, snippet}
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


class Case(Base):
    """Case Companion workspace."""
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    case_type = Column(String, nullable=True)  # property, consumer, employment, family...
    status = Column(String, default="open")
    notes = Column(Text, nullable=True)
    workflow = Column(JSON, nullable=True)  # generated workflow steps
    checklist = Column(JSON, nullable=True)  # checklist items
    prep_score = Column(Integer, default=0)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cases")


class DraftDocument(Base):
    """Generated legal drafts (RTI, complaint, notice, affidavit)."""
    __tablename__ = "drafts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    draft_type = Column(String, nullable=False)  # rti, complaint, notice, affidavit
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    template_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
