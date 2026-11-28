import io
import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.api.documents import upload_document
from app.services import doc_intelligence, rag_service, workflow_generator
from app.services.embed_service import EmbeddingService
from app.services.llm_service import LLMService, LLMUnavailable
from app.services.draft_generator import generate_draft


class FakeDB:
    def __init__(self): self.doc = None; self.rolled_back = False
    def add(self, obj): self.doc = obj
    def commit(self): pass
    def refresh(self, obj): obj.id = "document-id"
    def rollback(self): self.rolled_back = True


@pytest.mark.asyncio
async def test_upload_uses_opaque_path_and_keeps_display_name(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    file = UploadFile(filename="../../same name.txt", file=io.BytesIO(b"A readable text document."))
    db = FakeDB()
    await upload_document(BackgroundTasks(), file, db, type("User", (), {"id": "user-id"})())
    assert db.doc.filename == "same name.txt"
    assert ".." not in db.doc.file_path
    assert db.doc.file_path.endswith(".txt")
    assert db.doc.file_path != str(tmp_path / "user-id" / "same name.txt")


@pytest.mark.asyncio
async def test_upload_enforces_size_during_stream_and_cleans_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    file = UploadFile(filename="oversize.txt", file=io.BytesIO(b"x" * (1024 * 1024 + 1)))
    with pytest.raises(HTTPException) as err:
        await upload_document(BackgroundTasks(), file, FakeDB(), type("User", (), {"id": "u"})())
    assert err.value.status_code == 413
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_production_requires_strong_jwt_and_no_wildcard_cors():
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="x" * 40, cors_origins='["https://app.example"]')
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="a1BcDEf0123456789GhIjKlMnOpQrStUvWxYz", cors_origins='["*"]')


def test_signup_role_field_does_not_grant_privilege():
    from app.api.schemas import UserCreate
    user_input = UserCreate(email="user@example.com", password="a secure password", role="admin")
    assert user_input.role == "admin"  # accepted for backwards compatibility; route must ignore it
    import inspect
    from app.api import auth
    assert 'role="citizen"' in inspect.getsource(auth.signup)


@pytest.mark.asyncio
async def test_llm_missing_token_raises_instead_of_placeholder(monkeypatch):
    service = LLMService()
    service.token = ""
    with pytest.raises(LLMUnavailable):
        await service.chat([{"role": "user", "content": "question"}])


def test_hash_embedding_fallback_is_disabled():
    service = EmbeddingService()
    assert service.available is False
    with pytest.raises(RuntimeError, match="disabled"):
        service.encode_one("legal query")


@pytest.mark.asyncio
async def test_unavailable_llm_does_not_generate_document_analysis(monkeypatch):
    async def unavailable(*args, **kwargs): raise LLMUnavailable("offline")
    monkeypatch.setattr(doc_intelligence.llm_service, "chat", unavailable)
    result = await doc_intelligence.analyze_document("This is a sufficiently long legal document body.")
    assert result["analysis_status"] == "unavailable_model"
    assert "summary" not in result


@pytest.mark.asyncio
async def test_no_sources_returns_explicit_insufficient_sources(monkeypatch):
    async def empty(*args, **kwargs): return []
    monkeypatch.setattr(rag_service, "retrieve_context", empty)
    result = await rag_service.answer_question("What is the limitation period?")
    assert result["analysis_status"] == "unavailable_sources"
    assert result["sources"] == []
    assert "UNAVAILABLE" in result["answer"]


@pytest.mark.asyncio
async def test_workflow_fallback_is_labeled(monkeypatch):
    async def unavailable(*args, **kwargs): raise LLMUnavailable("offline")
    monkeypatch.setattr(workflow_generator.llm_service, "chat", unavailable)
    result = await workflow_generator.generate_workflow(description="A property issue")
    assert result["analysis_status"] == "template_fallback"
    assert "not legal deadlines" in result["deadline_notice"]


def test_draft_values_remain_plain_text_and_missing_fields_remain_explicit():
    generated = generate_draft("affidavit", {"deponent_name": "<script>alert(1)</script>"})
    assert "<script>alert(1)</script>" in generated
    assert "&lt;script&gt;" not in generated
    assert "<<FILL:" in generated
    assert "preliminary document only" in generated


def test_draft_rejects_unknown_or_non_scalar_fields():
    with pytest.raises(ValueError, match="Unknown draft fields"):
        generate_draft("affidavit", {"injected": "x"})
    with pytest.raises(ValueError, match="Invalid value"):
        generate_draft("affidavit", {"deponent_name": ["x"]})


def test_date_fallback_is_uncertain_not_legal_deadline():
    dates = doc_intelligence._regex_deadlines("Please attend on 03/04/2026 for the matter.")
    assert dates and dates[0]["confidence"] == "uncertain"
    assert "not a confirmed legal deadline" in dates[0]["description"]


def test_chat_response_exposes_unavailable_status():
    from app.api.schemas import ChatMessageOut
    response = ChatMessageOut(id="m1", role="assistant", content="[ANSWER UNAVAILABLE] no sources",
                              sources=[], analysis_status="unavailable_sources",
                              created_at=__import__("datetime").datetime.now())
    assert response.analysis_status == "unavailable_sources"


def test_other_user_cannot_read_document():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.db.session import Base
    from app.db.models import User, Document
    from app.api.documents import get_document
    from datetime import datetime
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(id="owner", email="owner@example.com", hashed_password="x")
        other = User(id="other", email="other@example.com", hashed_password="x")
        db.add_all([owner, other]); db.flush()
        doc = Document(id="private-doc", user_id=owner.id, filename="x.txt", file_path="/tmp/x.txt", file_type="txt", file_size=1)
        db.add(doc); db.commit()
        with pytest.raises(HTTPException) as err:
            get_document("private-doc", db, other)
        assert err.value.status_code == 404
    engine.dispose()


def test_workflow_schema_rejects_invalid_deadline_and_priority():
    from app.api.schemas import WorkflowOut
    with pytest.raises(ValidationError):
        WorkflowOut.model_validate({"case_type": "other", "summary": "x", "steps": [{"step": 0, "title": "x", "description": "x", "deadline_days": -1, "priority": "urgent"}], "checklist": [], "prep_score": 101})


def test_signup_ignores_requested_admin_role():
    from app.api.auth import signup
    from app.api.schemas import UserCreate
    db = FakeDB()
    db.query = lambda model: type("Query", (), {"filter": lambda self, *args: self, "first": lambda self: None})()
    def persist(user):
        user.id = "created-user"
        user.preferred_language = "en"
        user.created_at = __import__("datetime").datetime.now()
    db.add = persist
    db.refresh = lambda user: None
    result = signup(UserCreate(email="new@example.com", password="a secure password", role="admin"), db)
    assert result.user.role == "citizen"


@pytest.mark.asyncio
async def test_upload_rejects_content_that_does_not_match_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    file = UploadFile(filename="not-a-pdf.pdf", file=io.BytesIO(b"plain text, not a PDF"))
    with pytest.raises(HTTPException) as err:
        await upload_document(BackgroundTasks(), file, FakeDB(), type("User", (), {"id": "u"})())
    assert err.value.status_code == 400
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


@pytest.mark.asyncio
async def test_asgi_upload_limit_stops_streaming_body(monkeypatch):
    from app.main import UploadLimitMiddleware
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    called = {"app": False}
    async def application(scope, receive, send):
        called["app"] = True
        await receive()
    middleware = UploadLimitMiddleware(application)
    sent = []
    async def send(message): sent.append(message)
    body = b"x" * (1024 * 1024 + 256 * 1024 + 1)
    consumed = False
    async def receive():
        nonlocal consumed
        if not consumed:
            consumed = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}
    scope = {"type": "http", "method": "POST", "path": "/api/documents/upload", "headers": []}
    await middleware(scope, receive, send)
    assert called["app"] is True
    assert sent[0]["status"] == 413


@pytest.mark.asyncio
async def test_malformed_model_analysis_is_unavailable(monkeypatch):
    responses = iter(['{"doc_type":"legal_notice","case_type_hint":"civil_suit"}', '{"summary":"fabricated without required fields"}'])
    async def malformed(*args, **kwargs): return next(responses)
    monkeypatch.setattr(doc_intelligence.llm_service, "chat", malformed)
    result = await doc_intelligence.analyze_document("A sufficiently long document body for analysis.")
    assert result["analysis_status"] == "unavailable_model"
    assert "summary" not in result


@pytest.mark.asyncio
async def test_retrieval_rejects_passages_not_in_reviewed_registry(monkeypatch):
    monkeypatch.setattr(settings, "embedding_enabled", True)
    monkeypatch.setattr(rag_service.embedding_service, "encode_one", lambda query: [0.1])
    monkeypatch.setattr(rag_service, "load_registry", lambda: [])
    monkeypatch.setattr(rag_service.vector_store, "search", lambda *args, **kwargs: [
        {"title": "Cited item", "text": "content", "source_url": "https://indiacode.gov.in/act/example",
         "jurisdiction": "India", "reviewed_at": "2026-11-27", "score": 0.8},
    ])
    results = await rag_service.retrieve_context("query")
    assert results == []


def test_production_secret_must_have_high_entropy():
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="abcdefghabcdefghabcdefghabcdefgh", cors_origins='["https://app.example"]')


def test_malformed_cors_origins_fail_configuration():
    with pytest.raises(ValidationError):
        Settings(cors_origins="not-json")


def test_passwords_over_bcrypt_byte_limit_are_rejected():
    from app.api.schemas import UserCreate
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="é" * 37)
    from app.core.security import hash_password, verify_password
    with pytest.raises(ValueError):
        hash_password("x" * 73)
    assert verify_password("x" * 73, "not-a-hash") is False


def test_workflow_request_requires_description_or_document():
    from app.api.schemas import WorkflowRequest
    with pytest.raises(ValidationError):
        WorkflowRequest()
