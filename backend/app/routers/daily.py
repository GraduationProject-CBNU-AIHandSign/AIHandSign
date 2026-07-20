from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DailyWord, Word, LearningLog
from datetime import date

router = APIRouter(prefix="/daily", tags=["daily"])

WORDS_PER_DAY = 5  # 하루 학습 단어 수

# 커리큘럼 일차별 단어 조회 (education.html 목차용)
@router.get("/curriculum/{day}", summary="커리큘럼 일차별 단어 조회", description="N일차에 해당하는 단어 5개를 word_id 순서대로 반환합니다.")
def get_curriculum_words(day: int, db: Session = Depends(get_db)):
    offset = (day - 1) * WORDS_PER_DAY
    words = db.query(Word).order_by(Word.word_id).offset(offset).limit(WORDS_PER_DAY).all()
    return [
        {
            "word_id": w.word_id,
            "word_name": w.word_name,
            "category": w.category,
            "difficulty": w.difficulty,
            "day_number": day
        }
        for w in words
    ]

# 오늘의 단어 조회 (없으면 생성)
@router.get("/{user_id}", summary="오늘의 단어 조회", description="진도표 방식으로 하루 5개 단어를 가져옵니다. 학습한 단어 수 기준으로 다음 5개를 자동 선정합니다.")
def get_daily_words(user_id: int, db: Session = Depends(get_db)):
    today = date.today()

    # 오늘 이미 생성됐는지 확인
    existing = db.query(DailyWord).filter(
        DailyWord.user_id == user_id,
        DailyWord.date == today
    ).all()

    if existing:
        words = []
        for dw in existing:
            word = db.query(Word).filter(Word.word_id == dw.word_id).first()
            words.append({
                "daily_id": dw.daily_id,
                "word_id": dw.word_id,
                "word_name": word.word_name if word else None,
                "is_completed": dw.is_completed,
                "day_number": dw.day_number if hasattr(dw, 'day_number') else 1
            })
        return words

    # 진도 계산 (학습 시도한 distinct word_id 개수)
    attempted_ids = db.query(LearningLog.word_id).filter(
        LearningLog.user_id == user_id
    ).distinct().all()
    progress = len(attempted_ids)

    # 진도 기반 다음 5개 단어 선정 (word_id 순서대로)
    day_number = progress // WORDS_PER_DAY + 1
    next_words = db.query(Word).order_by(Word.word_id).offset(progress).limit(WORDS_PER_DAY).all()

    if not next_words:
        return []

    # DB에 저장 후 반환
    result = []
    for word in next_words:
        new_daily = DailyWord(
            user_id=user_id,
            word_id=word.word_id,
            date=today,
            is_completed=False
        )
        db.add(new_daily)
        db.flush()
        result.append({
            "daily_id": new_daily.daily_id,
            "word_id": word.word_id,
            "word_name": word.word_name,
            "is_completed": False,
            "day_number": day_number
        })
    db.commit()

    return result

# 오늘의 단어 완료 처리
@router.patch("/{daily_id}/complete", summary="오늘의 단어 완료 처리", description="특정 단어 학습을 완료로 표시합니다.")
def complete_daily_word(daily_id: int, db: Session = Depends(get_db)):
    daily = db.query(DailyWord).filter(DailyWord.daily_id == daily_id).first()
    if not daily:
        raise HTTPException(status_code=404, detail="오늘의 단어를 찾을 수 없습니다")
    daily.is_completed = True
    db.commit()
    return {"message": "완료 처리됐습니다"}