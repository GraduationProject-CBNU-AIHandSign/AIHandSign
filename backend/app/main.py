from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import users, words, learning, daily, chat, badges, predict

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SORI 수어 학습 플랫폼 API",
    description="""
## SORI - AI 기반 한국 수어 학습 플랫폼 백엔드 API
 
### 주요 기능
- 👤 **사용자** - 회원가입, 로그인, 사용자 정보 조회
- 📖 **단어** - 3,000개 수어 단어 검색 및 조회
- 📝 **학습 기록** - 학습 결과 저장, 통계, 오답 노트
- 📅 **오늘의 단어** - AI 맞춤 추천 단어 10개
- 💬 **챗봇** - 대화 기록 저장 및 조회
- 🏅 **뱃지** - 학습 성취 뱃지 자동 지급
- 🎥 **실시간 수어 인식** - 웹캠 키포인트 → AI 모델 추론 (WebSocket)
 
### 서버 정보
- ngrok URL: https://antler-bulldog-puppet.ngrok-free.dev
    """,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(words.router)
app.include_router(learning.router)
app.include_router(daily.router)
app.include_router(chat.router)
app.include_router(badges.router)
app.include_router(predict.router)

@app.get("/")
def root():
    return {"message": "AI 수어 학습 플랫폼 API 서버 작동 중 🎉"}

@app.get("/health")
def health_check():
    return {"status": "ok"}