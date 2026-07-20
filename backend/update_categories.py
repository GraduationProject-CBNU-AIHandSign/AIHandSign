"""
카테고리 DB 업데이트 스크립트
실행: python update_categories.py
위치: C:\sign-language-api\ 에 복사 후 실행
"""

import openpyxl
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "sign_language")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"ssl": {"ssl_disabled": True}}
)

# 엑셀 파일 경로 (스크립트와 같은 폴더에 있어야 함)
EXCEL_PATH = "수어_단어_카테고리분류_v24.xlsx"

def load_category_map(path):
    """엑셀에서 {word_id: category} 딕셔너리 반환"""
    wb = openpyxl.load_workbook(path)
    ws = wb['전체 단어 목록']
    category_map = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        word_id, word, category = row[0], row[1], row[2]
        if word_id and category:
            category_map[int(word_id)] = category
    print(f"엑셀 로드 완료: {len(category_map)}개 단어")
    return category_map

def update_categories(category_map):
    """DB words 테이블 category 컬럼 업데이트"""
    with engine.connect() as conn:
        # category 컬럼 존재 확인
        result = conn.execute(text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'words' AND COLUMN_NAME = 'category'"
        ), {"db": DB_NAME})
        if not result.fetchone():
            print("category 컬럼이 없습니다. 컬럼 추가 중...")
            conn.execute(text(
                "ALTER TABLE words ADD COLUMN category VARCHAR(50) DEFAULT NULL"
            ))
            conn.commit()
            print("category 컬럼 추가 완료!")

        # 업데이트
        updated = 0
        for word_id, category in category_map.items():
            conn.execute(
                text("UPDATE words SET category = :cat WHERE word_id = :wid"),
                {"cat": category, "wid": word_id}
            )
            updated += 1
            if updated % 500 == 0:
                print(f"  {updated}개 처리 중...")

        conn.commit()
        print(f"\n✅ 완료! 총 {updated}개 단어 카테고리 업데이트")

        # 결과 확인
        result = conn.execute(text(
            "SELECT category, COUNT(*) as cnt FROM words GROUP BY category ORDER BY cnt DESC LIMIT 20"
        ))
        print("\n카테고리별 단어 수 (상위 20개):")
        for row in result:
            print(f"  {row[0]}: {row[1]}개")

if __name__ == "__main__":
    print("=== DB 카테고리 업데이트 시작 ===\n")
    category_map = load_category_map(EXCEL_PATH)
    update_categories(category_map)
