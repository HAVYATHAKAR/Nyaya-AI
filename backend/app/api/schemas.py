"""Pydantic schemas for API request/response validation."""
from typing import List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator


# ===== Auth =====
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = None
    role: str = "citizen"

    @field_validator("password")
    @classmethod
    def bcrypt_password_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed bcrypt's 72-byte limit")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def bcrypt_password_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed bcrypt's 72-byte limit")
        return value


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
    chat_id: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=12000)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[List[Any]]
    created_at: datetime
    model_config = {"from_attributes": True}

    @computed_field
    @property
    def analysis_status(self) -> str:
        return "unavailable" if self.content.startswith("[ANSWER UNAVAILABLE]") else "available"


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
    document_id: Optional[str] = Field(default=None, max_length=80)
    description: Optional[str] = Field(default=None, max_length=12000)
    case_type_hint: Optional[str] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def require_context(self):
        if not (self.description and self.description.strip()) and not self.document_id:
            raise ValueError("Provide a description or document_id")
        return self


class WorkflowStep(BaseModel):
    step: int = Field(ge=1, le=100)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    deadline_days: Optional[int] = Field(default=None, ge=0, le=3650)
    priority: Literal["high", "medium", "low"] = "medium"


class WorkflowOut(BaseModel):
    analysis_status: str = "available"
    deadline_notice: str = "Generated timeframes are planning estimates, not legally binding deadlines."
    case_type: Literal["property_dispute", "consumer_grievance", "employment_issue", "family_matter", "criminal", "tax_dispute", "rti_application", "civil_suit", "other"]
    summary: str = Field(min_length=1, max_length=4000)
    steps: List[WorkflowStep]
    checklist: List[str]
    prep_score: int = Field(default=0, ge=0, le=100)


# ===== Drafts =====
class DraftCreate(BaseModel):
    draft_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    fields: dict = Field(max_length=50)


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
