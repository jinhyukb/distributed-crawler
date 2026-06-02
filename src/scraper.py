import urllib.parse
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from src.models import BookData

logger = logging.getLogger("ScraperWorker")

class ScraperWorker:
    STAR_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

    def __init__(self, queue_manager, metrics_collector=None):
        self.queue_mgr = queue_manager
        self.metrics = metrics_collector
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MyDistributedBot/3.0"})
        self.results: List[BookData] = []

    def parse_books(self, html: str, base_url: str) -> List[dict]:
        soup = BeautifulSoup(html, "html.parser")
        book_pods = soup.select("article.product_pod")
        parsed_items = []
        for pod in book_pods:
            try:
                title_el = pod.select_one("h3 a")
                title = title_el["title"] if title_el else None
                price_el = pod.select_one("p.price_color")
                price = price_el.text if price_el else None
                availability_el = pod.select_one("p.availability")
                in_stock = "In stock" in availability_el.text if availability_el else False
                
                rating_el = pod.select_one("p.star-rating")
                rating = 0
                if rating_el:
                    classes = rating_el.get("class", [])
                    rating_word = next((c for c in classes if c != "star-rating"), None)
                    rating = self.STAR_MAP.get(rating_word, 0)

                href = title_el["href"] if title_el else ""
                full_url = urllib.parse.urljoin(base_url, href)

                parsed_items.append({
                    "title": title,
                    "price": price,
                    "in_stock": in_stock,
                    "rating": rating,
                    "detail_url": full_url
                })
            except Exception as e:
                logger.error(f"파싱 에러: {e}")
        return parsed_items

    def work_loop(self):
        while True:
            url = self.queue_mgr.pop_task()
            if not url:
                break
            try:
                import time
                start_time = time.time()
                response = self.session.get(url, timeout=5)
                latency = time.time() - start_time
                
                if response.status_code != 200:
                    if self.metrics:
                        self.metrics.record_failure("HTTP_ERROR", url, response.status_code)
                    continue

                if self.metrics:
                    self.metrics.record_success(latency)

                raw_items = self.parse_books(response.text, url)
                for raw in raw_items:
                    try:
                        self.results.append(BookData(**raw))
                    except Exception:
                        if self.metrics:
                            self.metrics.record_schema_error()
            except Exception as e:
                if self.metrics:
                    self.metrics.record_failure("CONNECTION_ERROR", url)
                logger.error(f"작업 오류: {e}")
