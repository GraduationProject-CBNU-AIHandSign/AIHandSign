from sqlalchemy import Column, Integer, String, Boolean, Float, Text, Date, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Word(Base):
    __tablename__ = "words"
    word_id = Column(Integer, primary_key=True, autoincrement=True)
    word_name = Column(String(100), nullable=False)
    category = Column(String(50))
    difficulty = Column(Float, default=0.5)
    created_at = Column(TIMESTAMP, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    streak = Column(Integer, default=0)
    last_study_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())

class LearningLog(Base):
    __tablename__ = "learning_log"
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.word_id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float)
    feedback = Column(Text)
    mode = Column(String(20), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class WordMotion(Base):
    __tablename__ = "word_motion"
    motion_id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey("words.word_id"), unique=True, nullable=False)
    gcs_path = Column(String(255), nullable=False)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.word_id"))
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class DailyWord(Base):
    __tablename__ = "daily_words"
    daily_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.word_id"), nullable=False)
    date = Column(Date, nullable=False)
    is_completed = Column(Boolean, default=False)

class Badge(Base):
    __tablename__ = "badges"
    badge_id = Column(Integer, primary_key=True, autoincrement=True)
    badge_name = Column(String(50), nullable=False)
    description = Column(String(255))
    condition_type = Column(String(50))
    condition_value = Column(Integer)

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.badge_id"), nullable=False)
    earned_at = Column(TIMESTAMP, server_default=func.now())