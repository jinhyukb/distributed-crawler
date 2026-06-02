import os
import logging
from concurrent.futures import ThreadPoolExecutor
from src.database import DatabasePipeline
from src.queue_manager import DistributedQueueManager, MockRedis
from src.scraper import ScraperWorker
from src.metrics import CrawlerMetricsCollector, AlertManager

logger = logging.getLogger("ContainerOrchestrator")

def main():
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    db_path = os.environ.get("DB_PATH", "data/service_crawler.db")

    try:
        import redis
        db_backend = redis.Redis(host=redis_host, port=redis_port, db=0, socket_timeout=3)
        db_backend.ping()
        logger.info("실제 Redis 서버 연결 성공")
    except Exception:
        db_backend = MockRedis()
        logger.warning("MockRedis 가상 백엔드로 작동합니다.")

    pipeline = DatabasePipeline(db_path=db_path)
    qm = DistributedQueueManager(db_backend)
    metrics = CrawlerMetricsCollector()
    alert_mgr = AlertManager(metrics)
    
    # 초기 주소 적재
    target_pages = [
        "https://books.toscrape.com/catalogue/page-1.html",
        "https://books.toscrape.com/catalogue/page-2.html",
        "https://books.toscrape.com/catalogue/page-3.html"
    ]
    for page in target_pages:
        qm.push_task(page)

    worker = ScraperWorker(qm, metrics)
    
    logger.info("멀티 워커 가동을 개시합니다.")
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ComposeWorker") as executor:
        futures = [executor.submit(worker.work_loop) for _ in range(3)]
        for future in futures:
            future.result()

    total, written = pipeline.bulk_insert_books(worker.results)
    stats = pipeline.get_summary_statistics()
    
    logger.info(f"수집 완료. 누적 저장 데이터 수: {stats.get('total_count', 0)}개")
    alert_mgr.check_thresholds_and_alert()

if __name__ == "__main__":
    main()
