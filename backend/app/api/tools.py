"""Workflow + draft endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..db.session import get_db
from ..db.models import User, Document, Case, DraftDocument
from .schemas import (
    WorkflowRequest, WorkflowOut, DraftCreate, DraftOut,
    MessageOut,
)
from ..services.workflow_generator import generate_workflow
from ..services.draft_generator import list_templates, generate_draft


router = APIRouter(prefix="/api/tools", tags=["workflow+drafts"])


# ===== Workflow =====

@router.post("/workflow", response_model=WorkflowOut)
async def create_workflow(
    payload: WorkflowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a workflow based on uploaded doc or free-form description."""
    doc_context = None
    case_type_hint = payload.case_type_hint

    if payload.document_id:
        doc = (
            db.query(Document)
            .filter(Document.id == payload.document_id, Document.user_id == current_user.id)
            .first()
        )
        if doc:
            doc_context = (doc.ocr_text or "")[:3000]
            if doc.doc_type:
                case_type_hint = case_type_hint or doc.doc_type

    description = payload.description or "(based on uploaded document)"
    workflow = await generate_workflow(
        description=description,
        doc_context=doc_context,
        case_type_hint=case_type_hint,
    )
    return workflow


# ===== Drafts =====

@router.get("/drafts/templates")
def get_draft_templates():
    """List all available draft templates + their fields."""
    return list_templates()


@router.post("/drafts", response_model=DraftOut)
def create_draft(
    payload: DraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a legal draft from a template."""
    try:
        content = generate_draft(payload.draft_type, payload.fields)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Draft generation failed: {e}")

    draft = DraftDocument(
        user_id=current_user.id,
        draft_type=payload.draft_type,
        title=payload.title,
        content=content,
        template_used=payload.draft_type,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/drafts", response_model=list[DraftOut])
def list_drafts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(DraftDocument)
        .filter(DraftDocument.user_id == current_user.id)
        .order_by(DraftDocument.created_at.desc())
        .all()
    )


@router.get("/drafts/{draft_id}", response_model=DraftOut)
def get_draft(
    draft_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    d = (
        db.query(DraftDocument)
        .filter(DraftDocument.id == draft_id, DraftDocument.user_id == current_user.id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Draft not found")
    return d
