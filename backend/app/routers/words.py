from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Word

router = APIRouter(prefix="/words", tags=["words"])

# 전체 단어 목록 (페이지네이션)
@router.get("/", summary="전체 단어 목록 조회", description="3,000개 수어 단어 목록을 페이지 단위로 가져옵니다. skip(건너뛰기)과 limit(개수)으로 조절합니다.")
def get_words(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    words = db.query(Word).order_by(Word.word_id).offset(skip).limit(limit).all()
    return [
        {
            "word_id": w.word_id,
            "word_name": w.word_name,
            "category": w.category,
            "difficulty": w.difficulty
        }
        for w in words
    ]

# 카테고리별 단어 조회
@router.get("/category/{category}", summary="카테고리별 단어 조회", description="카테고리 이름으로 해당 단어들을 조회합니다. 예: 음식, 가족, 인사")
def get_words_by_category(category: str, db: Session = Depends(get_db)):
    words = db.query(Word).filter(Word.category == category).all()
    return [
        {
            "word_id": w.word_id,
            "word_name": w.word_name,
            "category": w.category,
            "difficulty": w.difficulty
        }
        for w in words
    ]

# 단어 검색
@router.get("/search/{keyword}", summary="단어 검색", description="키워드로 수어 단어를 검색합니다. 사전 검색 기능에 사용됩니다.")
def search_words(keyword: str, db: Session = Depends(get_db)):
    words = db.query(Word).filter(Word.word_name.contains(keyword)).all()
    return [
        {
            "word_id": w.word_id,
            "word_name": w.word_name,
            "category": w.category,
            "difficulty": w.difficulty
        }
        for w in words
    ]

# 단어 상세 조회
@router.get("/{word_id}", summary="단어 상세 조회", description="word_id로 특정 단어의 상세 정보를 가져옵니다. 아바타 JSON은 GCS에서 별도로 가져옵니다.")
def get_word(word_id: int, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.word_id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="단어를 찾을 수 없습니다")
    return {
        "word_id": word.word_id,
        "word_name": word.word_name,
        "category": word.category,
        "difficulty": word.difficulty
    }