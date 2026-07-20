"""
word_motion 테이블에 GCS 경로 3,000개 자동 삽입 스크립트
실행: python insert_word_motion.py
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"ssl": {"ssl_disabled": True}}
)

GCS_BASE = "https://storage.googleapis.com/sign-language-data-2026/processed/avatars_3d"

def insert_word_motions():
    with engine.connect() as conn:
        # 기존 데이터 확인
        result = conn.execute(text("SELECT COUNT(*) FROM word_motion"))
        count = result.scalar()
        print(f"현재 word_motion 테이블 데이터 수: {count}")

        if count >= 3000:
            print("이미 데이터가 채워져 있습니다!")
            return

        # 3,000개 INSERT
        print("word_motion 테이블 채우는 중...")
        for word_id in range(1, 3001):
            filename = f"WORD{word_id:04d}.json"
            gcs_path = f"{GCS_BASE}/{filename}"

            conn.execute(text("""
                INSERT INTO word_motion (word_id, gcs_path)
                VALUES (:word_id, :gcs_path)
                ON DUPLICATE KEY UPDATE gcs_path = :gcs_path
            """), {"word_id": word_id, "gcs_path": gcs_path})

            if word_id % 500 == 0:
                print(f"  {word_id}/3000 완료...")

        conn.commit()
        print("✅ 완료! 3,000개 경로 삽입 완료")

if __name__ == "__main__":
    insert_word_motions()