from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.database import get_db
from app.models import LearningLog, Word
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/learning", tags=["learning"])

# 요청 스키마
class LearningLogCreate(BaseModel):
    user_id: int
    word_id: int
    is_correct: bool
    score: Optional[float] = None
    feedback: Optional[str] = None
    mode: str  # chatbot / daily / retry / quiz

# 학습 기록 저장
@router.post("/log", summary="학습 기록 저장", description="단어 학습 결과를 저장합니다. mode는 chatbot/daily/retry/quiz 중 하나입니다.")
def create_log(log: LearningLogCreate, db: Session = Depends(get_db)):
    new_log = LearningLog(
        user_id=log.user_id,
        word_id=log.word_id,
        is_correct=log.is_correct,
        score=log.score,
        feedback=log.feedback,
        mode=log.mode
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return {"message": "학습 기록 저장 완료", "log_id": new_log.log_id}

# 사용자 학습 기록 조회
@router.get("/{user_id}", summary="학습 기록 조회", description="특정 사용자의 전체 학습 기록을 가져옵니다.")
def get_logs(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(LearningLog).filter(LearningLog.user_id == user_id).all()
    return [
        {
            "log_id": l.log_id,
            "word_id": l.word_id,
            "is_correct": l.is_correct,
            "score": l.score,
            "feedback": l.feedback,
            "mode": l.mode,
            "created_at": l.created_at
        }
        for l in logs
    ]

# 사용자 통계 조회
@router.get("/{user_id}/stats", summary="학습 통계 조회", description="총 학습 수, 정답 수, 오답 수, 정답률을 반환합니다.")
def get_stats(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(LearningLog).filter(LearningLog.user_id == user_id).all()
    total = len(logs)
    correct = sum(1 for l in logs if l.is_correct)
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    # 중복 제거한 학습 단어 수
    learned_words = db.query(LearningLog.word_id).filter(
        LearningLog.user_id == user_id
    ).distinct().count()

    return {
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "accuracy": accuracy,
        "learned_words": learned_words
    }

# 오답 노트 조회 (중복 제거 + 단어 정보 포함)
@router.get("/{user_id}/wrong", summary="오답 노트 조회", description="틀린 단어들만 중복 없이 모아서 반환합니다. 오답 복습 기능에 사용됩니다.")
def get_wrong_words(user_id: int, db: Session = Depends(get_db)):
    wrong_ids = db.query(LearningLog.word_id).filter(
        LearningLog.user_id == user_id,
        LearningLog.is_correct == False
    ).distinct().all()

    result = []
    for (word_id,) in wrong_ids:
        word = db.query(Word).filter(Word.word_id == word_id).first()
        if word:
            result.append({
                "word_id": word_id,
                "word_name": word.word_name,
                "category": word.category
            })
    return result