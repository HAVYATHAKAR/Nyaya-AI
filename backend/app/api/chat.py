"""Chat endpoints: list chats, create chat, send message → AI answer."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.deps import get_current_user
from ..db.session import get_db
from ..db.models import User, Chat, ChatMessage
from .schemas import (
    ChatCreate, ChatOut, ChatMessageCreate, ChatMessageOut, ChatAnswer
)
from ..services.rag_service import answer_question, retrieval_status


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/status")
def chat_status():
    status = retrieval_status()
    messages = {
        "available": "Reviewed legal sources are indexed and available for retrieval.",
        "unavailable_sources": "Legal Q&A is disabled until sources have completed dated review.",
        "unavailable_model": "The configured legal embedding model is unavailable.",
        "unavailable_storage": "Persistent legal-source storage is not configured.",
        "unavailable_empty_index": "No reviewed legal sources are currently indexed.",
        "unavailable_index": "The legal source index is unavailable or incompatible.",
    }
    return {"analysis_status": status, "message": messages.get(status, "Legal Q&A is unavailable.")}


@router.get("", response_model=list[ChatOut])
def list_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .order_by(Chat.created_at.desc())
        .all()
    )


@router.post("", response_model=ChatOut)
def create_chat(
    payload: ChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = Chat(user_id=current_user.id, title=payload.title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("/{chat_id}", response_model=ChatOut)
def get_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat


@router.post("/message", response_model=ChatMessageOut)
async def send_message(
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == payload.chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(404, "Chat not found")

    # Save user message
    user_msg = ChatMessage(chat_id=chat.id, role="user", content=payload.content,
                           analysis_status="not_applicable", sources=[])
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Build history for context
    history = [
        {"role": m.role, "content": m.content}
        for m in chat.messages[:-1]  # exclude the one we just added
    ]

    # Get RAG-grounded answer
    result = await answer_question(payload.content, history=history)

    # Save assistant message
    ai_msg = ChatMessage(
        chat_id=chat.id,
        role="assistant",
        content=result["answer"],
        sources=result.get("sources", []),
        analysis_status=result.get("analysis_status", "unavailable_index"),
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    return ai_msg


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(404, "Chat not found")
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted"}
