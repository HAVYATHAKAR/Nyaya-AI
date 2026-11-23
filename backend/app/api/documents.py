"""Document endpoints: upload, list, get, analyze."""
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.deps import get_current_user
from ..db.session import get_db
from ..db.models import User, Document
from .schemas import DocumentOut, MessageOut
from ..services.ocr_service import ocr_service
from ..services.doc_intelligence import analyze_document


router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".txt"}


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXT}")

    # Save file
    save_dir = settings.upload_path / current_user.id
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{file.filename}"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = save_path.stat().st_size
    if file_size > settings.max_upload_mb * 1024 * 1024:
        save_path.unlink(missing_ok=True)
        raise HTTPException(413, f"File too large (max {settings.max_upload_mb}MB)")

    # Create document record
    doc = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(save_path),
        file_type=ext.lstrip("."),
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Run analysis in background
    background_tasks.add_task(_analyze_document_task, doc.id)

    return doc


def _analyze_document_task(doc_id: str):
    """Background task: OCR + AI analysis."""
    from ..db.session import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return
        try:
            # 1. OCR
            ocr_text = ocr_service.extract_text(doc.file_path)
            doc.ocr_text = ocr_text

            # 2. AI analysis (run async function synchronously)
            import asyncio
            analysis = asyncio.run(analyze_document(ocr_text))

            # 3. Update doc
            doc.doc_type = analysis.get("doc_type", "other")
            doc.summary = analysis.get("summary")
            doc.plain_explanation = analysis.get("plain_explanation")
            doc.deadlines = analysis.get("deadlines", [])
            doc.key_entities = analysis.get("key_entities", [])
            doc.missing_info = analysis.get("missing_info", [])
            doc.status = "analyzed"

            from datetime import datetime
            doc.analyzed_at = datetime.utcnow()
        except Exception as e:
            doc.status = "failed"
            doc.error = str(e)
        db.commit()
    finally:
        db.close()


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/{doc_id}/reanalyze", response_model=MessageOut)
def reanalyze(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = "processing"
    db.commit()
    background_tasks.add_task(_analyze_document_task, doc.id)
    return {"message": "Re-analysis started"}
