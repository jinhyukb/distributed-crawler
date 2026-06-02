import sqlite3
import os
import re
import random
import logging
import requests
import urllib3
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from src.models import BookData

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request


logger = logging.getLogger("API_Server")

app = FastAPI(
    title="도서 데이터 제공 서비스 (Book Search API)",
    description="로컬 DB ➡️ Google (1차) ➡️ Open Library (2차) ➡️ Gutendex (3차) 연동 트리플 복선 검색 서버입니다.",
    version="3.6.0"
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

def fetch_from_google_books(query_str: str) -> List[dict]:
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query_str, "maxResults": 10}
    parsed = []
    try:
        print(f"[진단-구글-1] Google Books API 호출 전송 중... (검색어: '{query_str}')")
        res = requests.get(url, params=params, timeout=5)
        print(f"[진단-구글-2] Google 응답 코드: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            items = data.get("items", [])
            if isinstance(items, list):
                for item in items:
                    v_info = item.get("volumeInfo", {})
                    title = v_info.get("title", "Unknown Title")
                    authors = v_info.get("authors", ["Unknown Author"])
                    author = ", ".join([str(a) for a in authors if a]) if isinstance(authors, list) else "Unknown Author"
                    description = v_info.get("description", f"An amazing book titled '{title}' written by {author}.")
                    
                    detail_url = v_info.get("canonicalVolumeLink", "https://books.google.com")
                    img_links = v_info.get("imageLinks", {})
                    image_url = img_links.get("thumbnail", img_links.get("smallThumbnail", "https://books.google.com/googlebooks/images/no_cover_thumb.gif"))
                    if image_url.startswith("http://"):
                        image_url = image_url.replace("http://", "https://")
                    
                    price = round(random.uniform(10.0, 45.0), 2)
                    parsed.append({
                        "title": str(title), "price": float(price), "in_stock": True, "rating": 5,
                        "detail_url": str(detail_url), "image_url": str(image_url), "author": str(author), "description": str(description)
                    })
    except Exception as e:
        print(f"[진단-구글-오류] Google 호출 예외: {e}")
    return parsed

def fetch_from_open_library(query_str: str) -> List[dict]:
    url = "https://openlibrary.org/search.json"
    params = {"q": query_str, "limit": 10}
    parsed = []
    try:
        print(f"[진단-백업망-1] Open Library API 연동 개시... (검색어: '{query_str}')")
        res = requests.get(url, params=params, timeout=15)
        print(f"[진단-백업망-2] Open Library 응답 코드: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            docs = data.get("docs", [])
            print(f"[진단-백업망-3] 파싱된 책 노드 수: {len(docs)}개")
            for doc in docs:
                title = doc.get("title", "Unknown Title")
                authors = doc.get("author_name")
                author = ", ".join([str(a) for a in authors if a]) if isinstance(authors, list) else "Unknown Author"
                
                key = doc.get("key", "")
                detail_url = f"https://openlibrary.org{key}" if key else "https://openlibrary.org"
                
                cover_i = doc.get("cover_i")
                image_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else "https://openlibrary.org/images/icons/avatar_book-sm.png"
                
                description = f"An exceptional book titled '{title}' written by the distinguished author {author}."
                price = round(random.uniform(10.0, 45.0), 2)
                
                parsed.append({
                    "title": str(title), "price": float(price), "in_stock": True, "rating": 5,
                    "detail_url": str(detail_url), "image_url": str(image_url), "author": str(author), "description": str(description)
                })
    except Exception as e:
        print(f"[진단-백업망-오류] Open Library API 호출 예외: {e}")
    return parsed

def fetch_from_gutendex(query_str: str) -> List[dict]:
    url = "https://gutendex.com/books/"
    params = {"search": query_str}
    parsed = []
    try:
        print(f"[진단-고전망-1] Gutendex API 연동 개시... (검색어: '{query_str}')")
        res = requests.get(url, params=params, timeout=5)
        print(f"[진단-고전망-2] Gutendex 응답 코드: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            results = data.get("results", [])
            print(f"[진단-고전망-3] 파싱된 책 노드 수: {len(results)}개")
            for book in results:
                title = book.get("title", "Unknown Title")
                authors_list = book.get("authors", [])
                if authors_list and isinstance(authors_list, list):
                    author = authors_list[0].get("name", "Unknown Author")
                else:
                    author = "Unknown Author"
                
                book_id = book.get("id")
                detail_url = f"https://www.gutenberg.org/ebooks/{book_id}" if book_id else "https://www.gutenberg.org"
                
                formats = book.get("formats", {})
                image_url = formats.get("image/jpeg", "https://books.google.com/googlebooks/images/no_cover_thumb.gif")
                
                description = f"A timeless classic book titled '{title}' written by the distinguished author {author}."
                price = round(random.uniform(10.0, 45.0), 2)
                
                parsed.append({
                    "title": str(title), "price": float(price), "in_stock": True, "rating": 5,
                    "detail_url": str(detail_url), "image_url": str(image_url), "author": str(author), "description": str(description)
                })
    except Exception as e:
        print(f"[진단-고전망-오류] Gutendex API 호출 예외: {e}")
    return parsed

@app.get("/api/v1/books/search", response_model=List[BookResponse], tags=["Books"])
def search_books(
    q: str = Query(..., min_length=1, description="검색할 도서 키워드 (한글/영어 모두 지원)"),
    db: sqlite3.Connection = Depends(get_db)
):
    search_query = q
    print(f"\n==========================================")
    print(f"[요청 수신] 실시간 검색 수행중 ➡️ 검색어: '{q}'")
    print(f"==========================================")
    
    if re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', q):
        try:
            translated = GoogleTranslator(source='ko', target='en').translate(q)
            print(f"[번역 성공] 번역 결과: '{q}' ➡️ '{translated}'")
            search_query = translated
        except Exception as e:
            print(f"[번역 실패] 번역기 외부망 차단: {e}")

    query = """
    SELECT id, title, price, in_stock, rating, detail_url, image_url, author, description, scraped_at 
    FROM books 
    WHERE title LIKE ? OR author LIKE ? OR description LIKE ?;
    """
    like_param = f"%{search_query}%"
    cursor = db.cursor()
    cursor.execute(query, (like_param, like_param, like_param))
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]

    print(f"[1단계 로컬 DB] 로컬 데이터 기 검색 매치 수: {len(results)}개")

    if len(results) == 0:
        print("[2단계 오픈 API] 로컬 결과 없음 ➡️ 1차 Google Books API 호출")
        external_books = fetch_from_google_books(search_query)
        
        if not external_books:
            print("[경고] Google API 차단 감지 ➡️ 2차 Open Library 우회 백업망 가동")
            external_books = fetch_from_open_library(search_query)
            
        if not external_books:
            print("[경고] Open Library 지연 감지 ➡️ 3차 Gutendex 초고속 우회망 가동")
            external_books = fetch_from_gutendex(search_query)
            
        print(f"[데이터 수합] 최종 로드 성공 수량: {len(external_books)}개")
        
        valid_books = []
        for eb in external_books:
            try:
                valid_books.append(BookData(**eb))
            except Exception as ve:
                continue
        
        print(f"[유효성 정제] 최종 저장 유효 도서 수: {len(valid_books)}개")
        
        if valid_books:
            insert_query = """
            INSERT INTO books (title, price, in_stock, rating, detail_url, image_url, author, description, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(detail_url) DO UPDATE SET
                price = excluded.price,
                in_stock = excluded.in_stock,
                rating = excluded.rating,
                image_url = excluded.image_url,
                author = excluded.author,
                description = excluded.description,
                scraped_at = excluded.scraped_at;
            """
            insert_data = [
                (
                    b.title, b.price, 1 if b.in_stock else 0, b.rating, 
                    str(b.detail_url), str(b.image_url), b.author, b.description, 
                    b.scraped_at.strftime("%Y-%m-%d %H:%M:%S")
                )
                for b in valid_books
            ]
            try:
                cursor.executemany(insert_query, insert_data)
                db.commit()
                print(f"[로컬 캐싱 성공] 외부 도서 {len(valid_books)}개 데이터베이스 저장 완료")
            except Exception as db_err:
                print(f"[DB 에러] 트랜잭션 실패: {db_err}")

            cursor.execute(query, (like_param, like_param, like_param))
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]

    return results
