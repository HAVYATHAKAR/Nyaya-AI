"""Route-level API tests using an isolated SQLite database and mocked services."""
import io

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.db.models import Base, Chat, Document, DraftDocument
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def api(tmp_path, monkeypatch):
    """An ASGI client whose requests all use a fresh in-memory SQLite DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(get_current_user, None)
    monkeypatch.setattr("app.core.config.settings.upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr("app.core.config.settings.max_upload_mb", 1)
    monkeypatch.setattr("app.core.config.settings.cors_origins", '["http://testclient.local"]')

    # The upload response still exercises persistence and route validation, but its
    # background pipeline is replaced so tests never invoke OCR or a model.
    from app.api import documents as documents_api
    monkeypatch.setattr(documents_api, "_analyze_document_task", lambda doc_id: None)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, TestingSession
    app.dependency_overrides.clear()
    engine.dispose()


def _bearer(response):
    payload = response.json() if hasattr(response, "json") else response
    return {"Authorization": f"Bearer {payload['access_token']}"}


async def _signup(client, email, name="Test User", role="citizen"):
    return await client.post("/api/auth/signup", json={
        "email": email, "password": "a secure password", "name": name, "role": role,
    })


@pytest.mark.asyncio
async def test_auth_signup_login_me_and_auth_failures(api):
    client, _ = api
    created = await _signup(client, "one@example.com", role="admin")
    assert created.status_code == 201
    body = created.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "one@example.com"
    assert body["user"]["role"] == "citizen"

    me = await client.get("/api/auth/me", headers=_bearer(body))
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]

    login = await client.post("/api/auth/login", json={
        "email": "one@example.com", "password": "a secure password",
    })
    assert login.status_code == 200
    assert login.json()["user"]["id"] == body["user"]["id"]

    duplicate = await _signup(client, "one@example.com")
    assert duplicate.status_code == 400
    bad_login = await client.post("/api/auth/login", json={
        "email": "one@example.com", "password": "incorrect",
    })
    assert bad_login.status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})).status_code == 401


@pytest.mark.asyncio
async def test_document_upload_list_get_reanalyze_and_ownership(api):
    client, _ = api
    first = await _signup(client, "doc-owner@example.com")
    second = await _signup(client, "doc-other@example.com")
    owner_headers, other_headers = _bearer(first.json()), _bearer(second.json())

    upload = await client.post(
        "/api/documents/upload", headers=owner_headers,
        files={"file": ("notice.txt", io.BytesIO(b"Readable legal document content, sufficiently long."), "text/plain")},
    )
    assert upload.status_code == 200
    doc = upload.json()
    assert doc["filename"] == "notice.txt"
    assert doc["file_type"] == "txt"
    assert doc["status"] == "processing"

    listed = await client.get("/api/documents", headers=owner_headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [doc["id"]]
    assert (await client.get(f"/api/documents/{doc['id']}", headers=owner_headers)).status_code == 200
    assert (await client.get(f"/api/documents/{doc['id']}", headers=other_headers)).status_code == 404
    assert (await client.get("/api/documents", headers=other_headers)).json() == []

    reanalysis = await client.post(f"/api/documents/{doc['id']}/reanalyze", headers=owner_headers)
    assert reanalysis.status_code == 200
    assert reanalysis.json() == {"message": "Re-analysis started"}
    assert (await client.post(f"/api/documents/{doc['id']}/reanalyze", headers=other_headers)).status_code == 404

    unsupported = await client.post(
        "/api/documents/upload", headers=owner_headers,
        files={"file": ("script.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert unsupported.status_code == 400
    malformed = await client.post(
        "/api/documents/upload", headers=owner_headers,
        files={"file": ("not-pdf.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
    )
    assert malformed.status_code == 400


@pytest.mark.asyncio
async def test_chat_create_message_history_delete_and_ownership(api, monkeypatch):
    client, _ = api
    owner = await _signup(client, "chat-owner@example.com")
    other = await _signup(client, "chat-other@example.com")
    owner_headers, other_headers = _bearer(owner.json()), _bearer(other.json())

    async def fake_answer(question, history=None):
        assert question == "What should I do?"
        assert history == []
        return {"answer": "[ANSWER UNAVAILABLE] No reviewed sources are indexed.", "sources": [], "analysis_status": "unavailable_sources"}

    monkeypatch.setattr("app.api.chat.answer_question", fake_answer)
    created = await client.post("/api/chat", headers=owner_headers, json={"title": "My case"})
    assert created.status_code == 200
    chat_id = created.json()["id"]
    assert created.json()["messages"] == []

    sent = await client.post("/api/chat/message", headers=owner_headers, json={
        "chat_id": chat_id, "content": "What should I do?",
    })
    assert sent.status_code == 200
    assert sent.json()["role"] == "assistant"
    assert sent.json()["analysis_status"] == "unavailable_sources"
    history = await client.get(f"/api/chat/{chat_id}", headers=owner_headers)
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]
    assert (await client.get("/api/chat", headers=owner_headers)).json()[0]["id"] == chat_id
    assert (await client.get(f"/api/chat/{chat_id}", headers=other_headers)).status_code == 404
    assert (await client.post("/api/chat/message", headers=other_headers, json={
        "chat_id": chat_id, "content": "private",
    })).status_code == 404
    assert (await client.delete(f"/api/chat/{chat_id}", headers=other_headers)).status_code == 404
    deleted = await client.delete(f"/api/chat/{chat_id}", headers=owner_headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Chat deleted"}
    assert (await client.get(f"/api/chat/{chat_id}", headers=owner_headers)).status_code == 404

    invalid = await client.post("/api/chat/message", headers=owner_headers, json={"chat_id": "", "content": ""})
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_workflow_validation_fallback_and_document_ownership(api, monkeypatch):
    client, _ = api
    owner = await _signup(client, "workflow-owner@example.com")
    other = await _signup(client, "workflow-other@example.com")
    owner_headers, other_headers = _bearer(owner.json()), _bearer(other.json())

    missing_context = await client.post("/api/tools/workflow", headers=owner_headers, json={})
    assert missing_context.status_code == 422

    from app.services import workflow_generator
    async def model_unavailable(*args, **kwargs):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(workflow_generator.llm_service, "chat", model_unavailable)

    fallback = await client.post("/api/tools/workflow", headers=owner_headers, json={
        "description": "I have a property ownership dispute", "case_type_hint": "property_dispute",
    })
    assert fallback.status_code == 200
    assert fallback.json()["analysis_status"] == "template_fallback"
    assert fallback.json()["case_type"] == "property_dispute"
    assert "not legal deadlines" in fallback.json()["deadline_notice"]

    # Seed an owned document through the test DB to exercise workflow context access.
    Session = api[1]
    with Session() as session:
        owner_id = owner.json()["user"]["id"]
        other_id = other.json()["user"]["id"]
        own_doc = Document(user_id=owner_id, filename="owned.txt", file_path="/tmp/owned.txt", ocr_text="An owned document with context.")
        foreign_doc = Document(user_id=other_id, filename="foreign.txt", file_path="/tmp/foreign.txt", ocr_text="Private context.")
        session.add_all([own_doc, foreign_doc])
        session.commit()
        own_id, foreign_id = own_doc.id, foreign_doc.id

    own_result = await client.post("/api/tools/workflow", headers=owner_headers, json={"document_id": own_id})
    assert own_result.status_code == 200
    assert (await client.post("/api/tools/workflow", headers=owner_headers, json={"document_id": foreign_id})).status_code == 404
    assert (await client.post("/api/tools/workflow", headers=other_headers, json={"document_id": own_id})).status_code == 404


@pytest.mark.asyncio
async def test_public_templates_and_draft_routes_with_ownership(api):
    client, Session = api
    owner = await _signup(client, "draft-owner@example.com")
    other = await _signup(client, "draft-other@example.com")
    owner_headers, other_headers = _bearer(owner.json()), _bearer(other.json())

    templates = await client.get("/api/tools/drafts/templates")
    assert templates.status_code == 200
    assert "affidavit" in templates.json()
    assert "fields" in templates.json()["affidavit"]
    assert (await client.get("/api/tools/drafts/templates", headers=other_headers)).status_code == 200

    draft_response = await client.post("/api/tools/drafts", headers=owner_headers, json={
        "draft_type": "affidavit", "title": "My affidavit", "fields": {"deponent_name": "A Person"},
    })
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["draft_type"] == "affidavit"
    assert draft["title"] == "My affidavit"
    assert "A Person" in draft["content"]
    assert (await client.get("/api/tools/drafts", headers=owner_headers)).json()[0]["id"] == draft["id"]
    assert (await client.get(f"/api/tools/drafts/{draft['id']}", headers=owner_headers)).status_code == 200
    assert (await client.get(f"/api/tools/drafts/{draft['id']}", headers=other_headers)).status_code == 404

    unknown = await client.post("/api/tools/drafts", headers=owner_headers, json={
        "draft_type": "unregistered", "title": "Invalid", "fields": {},
    })
    assert unknown.status_code == 400
    assert (await client.get("/api/tools/drafts", headers=other_headers)).json() == []

    # Confirm ownership persisted only to the creating account.
    with Session() as session:
        assert session.query(DraftDocument).filter_by(id=draft["id"], user_id=owner.json()["user"]["id"]).count() == 1
        assert session.query(Chat).count() == 0


@pytest.mark.asyncio
async def test_public_health_and_cors(api):
    client, _ = api
    health = await client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "semantic_retrieval" in health.json()

    preflight = await client.options("/api/auth/signup", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in preflight.headers["access-control-allow-methods"]
