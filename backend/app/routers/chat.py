from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatHistory
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/chat", tags=["chat"])

# 요청 스키마
class ChatCreate(BaseModel):
    user_id: int
    word_id: Optional[int] = None
    message: str
    response: str

# 대화 기록 저장
@router.post("/", summary="챗봇 대화 기록 저장", description="챗봇과의 대화 내용을 DB에 저장합니다. 사용자 메시지와 AI 응답을 함께 저장합니다.")
def save_chat(chat: ChatCreate, db: Session = Depends(get_db)):
    new_chat = ChatHistory(
        user_id=chat.user_id,
        word_id=chat.word_id,
        message=chat.message,
        response=chat.response
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return {"message": "대화 기록 저장 완료", "chat_id": new_chat.chat_id}

# 사용자 대화 기록 조회
@router.get("/{user_id}", summary="챗봇 대화 기록 조회", description="특정 사용자의 챗봇 대화 기록을 최신순으로 가져옵니다. limit으로 개수를 조절합니다.")
def get_chats(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
    return [
        {
            "chat_id": c.chat_id,
            "word_id": c.word_id,
            "message": c.message,
            "response": c.response,
            "created_at": c.created_at
        }
        for c in chats
    ]

# 대화 기록 삭제
@router.delete("/{chat_id}", summary="챗봇 대화 기록 삭제", description="특정 대화 기록을 삭제합니다.")
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    chat = db.query(ChatHistory).filter(ChatHistory.chat_id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="대화 기록을 찾을 수 없습니다")
    db.delete(chat)
    db.commit()
    return {"message": "대화 기록 삭제 완료"}