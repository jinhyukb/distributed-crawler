import sqlite3
import logging
from typing import List, Tuple
from pydantic import BaseModel

logger = logging.getLogger("DatabasePipeline")

class DatabasePipeline:
    def __init__(self, db_path: str = "data/service_crawler.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        schema_query = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            in_stock INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            detail_url TEXT UNIQUE NOT NULL,
            image_url TEXT NOT NULL,
            author TEXT NOT NULL,
            description TEXT NOT NULL,
            scraped_at TEXT NOT NULL
        );
        """
        index_query = "CREATE INDEX IF NOT EXISTS idx_books_price ON books (price);"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(schema_query)
            cursor.execute(index_query)
            conn.commit()

    def bulk_insert_books(self, books: List[BaseModel]) -> Tuple[int, int]:
        if not books:
            return 0, 0
        upsert_query = """
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
        data_to_insert = [
            (
                book.title, book.price, 1 if book.in_stock else 0, book.rating,
                str(book.detail_url), str(book.image_url), book.author, book.description,
                book.scraped_at.strftime("%Y-%m-%d %H:%M:%S")
            )
            for book in books
        ]
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(upsert_query, data_to_insert)
                conn.commit()
                return len(data_to_insert), cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"DB 벌크 적재 실패: {e}")
            raise e

    def get_summary_statistics(self) -> dict:
        query = "SELECT COUNT(*) as total_count, AVG(price) as avg_price, MAX(price) as max_price, MIN(price) as min_price FROM books;"
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.cursor().execute(query).fetchone()
            return dict(row) if row else {}
