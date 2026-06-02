import time
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("SystemMonitor")

class CrawlerMetricsCollector:
    def __init__(self):
        self.reset_metrics()

    def reset_metrics(self):
        self.start_time = datetime.utcnow()
        self.success_count = 0
        self.failed_count = 0
        self.schema_validation_errors = 0
        self.response_times: List[float] = []
        self.critical_errors: List[Dict[str, Any]] = []

    def record_success(self, response_time: float):
        self.success_count += 1
        self.response_times.append(response_time)

    def record_failure(self, error_type: str, url: str, status_code: int = 0):
        self.failed_count += 1
        self.critical_errors.append({
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "error_type": error_type,
            "url": url,
            "status_code": status_code
        })

    def record_schema_error(self):
        self.schema_validation_errors += 1

    @property
    def error_rate(self) -> float:
        total = self.success_count + self.failed_count
        return (self.failed_count / total) * 100 if total > 0 else 0.0

    @property
    def average_latency(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0

class AlertManager:
    def __init__(self, metrics_collector, slack_webhook_url: str = ""):
        self.metrics = metrics_collector
        self.slack_webhook_url = slack_webhook_url
        self.ERR_RATE_THRESHOLD = 20.0
        self.SCHEMA_ERR_THRESHOLD = 5

    def check_thresholds_and_alert(self) -> bool:
        alert_triggered = False
        if self.metrics.error_rate >= self.ERR_RATE_THRESHOLD:
            alert_triggered = True
            logger.error("🚨 에러 발생률 임계치 초과 경보 발생")
        elif self.metrics.schema_validation_errors >= self.SCHEMA_ERR_THRESHOLD:
            alert_triggered = True
            logger.warning("⚠️ 레이아웃 스키마 깨짐 감지 경보 발생")
        return alert_triggered
