from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from pydantic import BaseModel
import hashlib

router = APIRouter(prefix="/users", tags=["users"])

# 요청 스키마
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# 회원가입
@router.post("/register", summary="회원가입", description="이름, 이메일, 비밀번호로 새 계정을 만듭니다.")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 이메일 중복 확인
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 이메일입니다")
    
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입 성공", "user_id": new_user.user_id}

# 로그인
@router.post("/login", summary="로그인", description="이메일과 비밀번호로 로그인합니다. 성공 시 user_id를 반환합니다.")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="존재하지 않는 이메일입니다")
    if db_user.password_hash != hash_password(user.password):
        raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다")
    return {"message": "로그인 성공", "user_id": db_user.user_id, "name": db_user.name}

# 사용자 정보 조회
@router.get("/{user_id}", summary="사용자 정보 조회", description="user_id로 사용자 정보(이름, 이메일, 스트릭 등)를 조회합니다.")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "streak": user.streak,
        "created_at": user.created_at
    }