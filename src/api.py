import sqlite3
import os
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel
from src.models import BookData

app = FastAPI(
    title="도서 데이터 제공 서비스 (Book Search API)",
    description="크롤러를 통해 정제된 이커머스 도서 메타데이터를 공급하는 REST API 서버입니다.",
    version="1.0.0"
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

@app.get("/", tags=["Health Check"])
def read_root():
    return {
        "status": "healthy",
        "service": "Book Search REST API",
        "database_connected": os.path.exists(DB_PATH)
    }

@app.get("/api/v1/books", response_model=List[BookResponse], tags=["Books"])
def get_books(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 반환할 도서 수"),
    min_price: Optional[float] = Query(None, description="최소 가격 필터"),
    max_price: Optional[float] = Query(None, description="최대 가격 필터"),
    db: sqlite3.Connection = Depends(get_db)
):
    offset = (page - 1) * limit
    query = "SELECT id, title, price, in_stock, rating, detail_url, scraped_at FROM books WHERE 1=1"
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
def search_books_by_title(
    q: str = Query(..., min_length=1, description="검색할 도서 제목 키워드"),
    db: sqlite3.Connection = Depends(get_db)
):
    query = "SELECT id, title, price, in_stock, rating, detail_url, scraped_at FROM books WHERE title LIKE ?;"
    cursor = db.cursor()
    cursor.execute(query, (f"%{q}%",))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/v1/statistics", tags=["Statistics"])
def get_statistics(db: sqlite3.Connection = Depends(get_db)):
    query = "SELECT COUNT(*) as total_books, AVG(price) as average_price, SUM(CASE WHEN in_stock = 1 THEN 1 ELSE 0 END) as in_stock_books FROM books;"
    cursor = db.cursor()
    row = cursor.execute(query).fetchone()
    if not row or row["total_books"] == 0:
        return {"message": "계산 가능한 데이터가 존재하지 않습니다."}
    return {
        "total_collected": row["total_books"],
        "average_price": round(row["average_price"], 2),
        "in_stock_rate": f"{round((row['in_stock_books'] / row['total_books']) * 100, 1)}%"
    }
