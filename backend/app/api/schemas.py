"""Pydantic schemas for API request/response validation."""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ===== Auth =====
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    role: str = "citizen"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    role: str
    preferred_language: str
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ===== Documents =====
class DocumentOut(BaseModel):
    id: str
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    status: str
    doc_type: Optional[str]
    summary: Optional[str]
    plain_explanation: Optional[str]
    deadlines: Optional[List[Any]]
    key_entities: Optional[List[Any]]
    missing_info: Optional[List[Any]]
    ocr_text: Optional[str]
    error: Optional[str]
    created_at: datetime
    analyzed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ===== Chat =====
class ChatCreate(BaseModel):
    title: Optional[str] = "New conversation"


class ChatMessageCreate(BaseModel):
    chat_id: str
    content: str


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[List[Any]]
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: List[ChatMessageOut]
    model_config = {"from_attributes": True}


class ChatAnswer(BaseModel):
    answer: str
    sources: List[Any] = []


# ===== Workflow =====
class WorkflowRequest(BaseModel):
    """Generate a workflow based on document or case description."""
    document_id: Optional[str] = None
    description: Optional[str] = None
    case_type_hint: Optional[str] = None


class WorkflowStep(BaseModel):
    step: int
    title: str
    description: str
    deadline_days: Optional[int] = None
    priority: str = "medium"  # high|medium|low


class WorkflowOut(BaseModel):
    case_type: str
    summary: str
    steps: List[WorkflowStep]
    checklist: List[str]
    prep_score: int = 0


# ===== Drafts =====
class DraftCreate(BaseModel):
    draft_type: str  # rti|complaint|notice|affidavit|rental_agreement
    title: str
    fields: dict   # template variables


class DraftOut(BaseModel):
    id: str
    draft_type: str
    title: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ===== Generic =====
class HealthOut(BaseModel):
    status: str
    app: str
    version: str


class MessageOut(BaseModel):
    message: str
