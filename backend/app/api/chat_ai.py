from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_student
from app.schemas.chat_ai import (
    ChatSendMessageRequest,
    ChatSendMessageResponse,
    ChatThreadCreateRequest,
    ChatThreadListItem,
    ChatThreadResponse,
    ChatMessageResponse,
)
from app.services.chat_ai_service import (
    create_student_chat_thread,
    delete_student_chat_thread,
    get_student_chat_thread,
    list_student_chat_messages,
    list_student_chat_threads,
    send_student_chat_message,
)


router = APIRouter(prefix="/chat-with-ai", tags=["chat-with-ai"])


@router.post("/chats", response_model=ChatThreadResponse)
def create_chat_thread(
    request: ChatThreadCreateRequest,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    return create_student_chat_thread(db, user, request)


@router.get("/chats", response_model=list[ChatThreadListItem])
def list_chat_threads(user=Depends(require_student), db: Session = Depends(get_db)):
    return list_student_chat_threads(db, user)


@router.get("/chats/{chat_id}", response_model=ChatThreadResponse)
def get_chat_thread(
    chat_id: str,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    return get_student_chat_thread(db, user, chat_id)


@router.get("/chats/{chat_id}/messages", response_model=list[ChatMessageResponse])
def get_chat_messages(
    chat_id: str,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    return list_student_chat_messages(db, user, chat_id)


@router.post("/chats/{chat_id}/messages", response_model=ChatSendMessageResponse)
def send_chat_message(
    chat_id: str,
    request: ChatSendMessageRequest,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    return send_student_chat_message(db, user, chat_id, request.content)


@router.delete("/chats/{chat_id}")
def delete_chat_thread(
    chat_id: str,
    user=Depends(require_student),
    db: Session = Depends(get_db),
):
    delete_student_chat_thread(db, user, chat_id)
    return {"deleted": True}
