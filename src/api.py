import sqlite3
import os
import re
import logging
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from src.models import BookData

logger = logging.getLogger("API_Server")

app = FastAPI(
    title="도서 데이터 제공 서비스 (Book Search API)",
    description="한-영 번역 검색 및 다중 조건 부분 탐색이 연계된 고도화 검색 API 서버입니다.",
    version="2.0.0"
)

DB_PATH = os.environ.get("DB_PATH", "data/service_crawler.db")

class BookResponse(BookData):
    id: int

def get_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500, 
            detail="데이터베이스 파일이 존재하지 않습니다. 먼저 수집을 실행해 주세요."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@app.get("/api/v1/books", response_model=List[BookResponse], tags=["Books"])
def get_books(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 반환할 도서 수"),
    min_price: Optional[float] = Query(None, description="최소 가격 필터"),
    max_price: Optional[float] = Query(None, description="최대 가격 필터"),
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * limit
    query = "SELECT id, title, price, in_stock, rating, detail_url, image_url, author, description, scraped_at FROM books WHERE 1=1"
    params = []

    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = db.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/v1/books/search", response_model=List[BookResponse], tags=["Books"])
def search_books(
    q: str = Query(..., min_length=1, description="검색할 도서 키워드 (한글/영어 모두 지원)"),
    db: sqlite3.Connection = Depends(get_db)
):
    search_query = q
    
    if re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', q):
        try:
            translated = GoogleTranslator(source='ko', target='en').translate(q)
            logger.info(f"한글 검색 감지: '{q}' -> 영문 변환: '{translated}'")
            search_query = translated
        except Exception as e:
            logger.error(f"실시간 번역 필터 가동 오류: {e}")

    query = "SELECT id, title, price, in_stock, rating, detail_url, image_url, author, description, scraped_at FROM books WHERE title LIKE ? OR author LIKE ? OR description LIKE ?;"
    like_param = f"%{search_query}%"
    cursor = db.cursor()
    cursor.execute(query, (like_param, like_param, like_param))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
