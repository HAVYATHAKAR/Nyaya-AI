"""Document endpoints: safe upload, list, get, analyze."""
import asyncio
import os
import re
import uuid
from pathlib import Path
from datetime import datetime
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
CHUNK_BYTES = 1024 * 1024


@router.post("/upload", response_model=DocumentOut)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...),
                          db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    original = (file.filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    original = re.sub(r"[^A-Za-z0-9._ -]", "_", original).strip(" .")[:255] or "document"
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Unsupported file type")
    limit = settings.max_upload_mb * 1024 * 1024
    save_dir = settings.upload_path / current_user.id
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{uuid.uuid4().hex}{ext}"
    size = 0
    prefix = bytearray()
    try:
        with save_path.open("xb") as target:
            while chunk := await file.read(CHUNK_BYTES):
                if len(prefix) < 16:
                    prefix.extend(chunk[:16 - len(prefix)])
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"File too large (max {settings.max_upload_mb}MB)")
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        if size == 0:
            raise HTTPException(400, "Uploaded file is empty")
        signatures = {
            ".pdf": lambda data: data.startswith(b"%PDF-"),
            ".png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": lambda data: data.startswith(b"\xff\xd8\xff"),
            ".jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
            ".bmp": lambda data: data.startswith(b"BM"),
            ".tif": lambda data: data.startswith((b"II*\x00", b"MM\x00*")),
            ".tiff": lambda data: data.startswith((b"II*\x00", b"MM\x00*")),
        }
        if ext in signatures and not signatures[ext](bytes(prefix)):
            raise HTTPException(400, "File content does not match the selected file type")
        if ext == ".txt" and b"\x00" in prefix:
            raise HTTPException(400, "Unsupported text file content")
        doc = Document(user_id=current_user.id, filename=original, file_path=str(save_path),
                       file_type=ext.lstrip("."), file_size=size, status="processing")
        db.add(doc)
        db.commit()
        db.refresh(doc)
        background_tasks.add_task(_analyze_document_task, doc.id)
        return doc
    except HTTPException:
        save_path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, "Upload could not be saved")
    finally:
        await file.close()


def _analyze_document_task(doc_id: str):
    """Background task; never persists exception text or fabricated OCR output."""
    from ..db.session import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return
        try:
            ocr_text = ocr_service.extract_text(doc.file_path)
            if not ocr_text or len(ocr_text.strip()) < 20:
                doc.status = "failed"
                doc.error = "OCR unavailable or insufficient readable text; no legal analysis was generated."
                db.commit()
                return
            doc.ocr_text = ocr_text
            analysis = asyncio.run(analyze_document(ocr_text))
            if analysis.get("analysis_status") != "available":
                doc.status = "failed"
                doc.error = analysis.get("analysis_message", "AI analysis unavailable; no legal analysis was generated.")
                db.commit()
                return
            doc.doc_type = analysis.get("doc_type", "other")
            doc.summary = analysis.get("summary")
            doc.plain_explanation = analysis.get("plain_explanation")
            doc.deadlines = analysis.get("deadlines", [])
            doc.key_entities = analysis.get("key_entities", [])
            doc.missing_info = analysis.get("missing_info", [])
            doc.status = "analyzed"
            doc.error = None
            doc.analyzed_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc.status = "failed"
                doc.error = "Document processing failed; please retry or consult a professional."
                db.commit()
    finally:
        db.close()


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/{doc_id}/reanalyze", response_model=MessageOut)
def reanalyze(doc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    doc.status = "processing"
    doc.error = None
    db.commit()
    background_tasks.add_task(_analyze_document_task, doc.id)
    return {"message": "Re-analysis started"}
