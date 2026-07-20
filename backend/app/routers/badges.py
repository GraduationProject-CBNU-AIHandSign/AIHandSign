from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Badge, UserBadge, LearningLog, User
from pydantic import BaseModel

router = APIRouter(prefix="/badges", tags=["badges"])

# 전체 뱃지 목록
@router.get("/", summary="전체 뱃지 목록 조회", description="획득 가능한 모든 뱃지 목록과 조건을 반환합니다.")
def get_badges(db: Session = Depends(get_db)):
    badges = db.query(Badge).all()
    return [
        {
            "badge_id": b.badge_id,
            "badge_name": b.badge_name,
            "description": b.description,
            "condition_type": b.condition_type,
            "condition_value": b.condition_value
        }
        for b in badges
    ]

# 사용자 보유 뱃지 조회
@router.get("/{user_id}", summary="보유 뱃지 조회", description="특정 사용자가 획득한 뱃지 목록을 반환합니다.")
def get_user_badges(user_id: int, db: Session = Depends(get_db)):
    user_badges = db.query(UserBadge).filter(UserBadge.user_id == user_id).all()
    result = []
    for ub in user_badges:
        badge = db.query(Badge).filter(Badge.badge_id == ub.badge_id).first()
        result.append({
            "badge_id": badge.badge_id,
            "badge_name": badge.badge_name,
            "description": badge.description,
            "earned_at": ub.earned_at
        })
    return result

# 뱃지 자동 지급 (학습 후 호출)
@router.post("/{user_id}/check", summary="뱃지 자동 지급 확인", description="학습 완료 후 호출하면 조건을 충족한 뱃지를 자동으로 지급합니다. 학습 기록 저장 후 항상 호출하세요.")
def check_and_grant_badges(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(LearningLog).filter(LearningLog.user_id == user_id).all()
    total = len(logs)
    correct = sum(1 for l in logs if l.is_correct)
    user = db.query(User).filter(User.user_id == user_id).first()
    streak = user.streak if user else 0

    badges = db.query(Badge).all()
    granted = []

    for badge in badges:
        # 이미 보유 중인지 확인
        already = db.query(UserBadge).filter(
            UserBadge.user_id == user_id,
            UserBadge.badge_id == badge.badge_id
        ).first()
        if already:
            continue

        # 조건 확인
        if badge.condition_type == "words_learned" and total >= badge.condition_value:
            grant = True
        elif badge.condition_type == "correct" and correct >= badge.condition_value:
            grant = True
        elif badge.condition_type == "streak" and streak >= badge.condition_value:
            grant = True
        else:
            grant = False

        if grant:
            new_badge = UserBadge(user_id=user_id, badge_id=badge.badge_id)
            db.add(new_badge)
            granted.append(badge.badge_name)

    db.commit()
    return {"granted": granted, "count": len(granted)}