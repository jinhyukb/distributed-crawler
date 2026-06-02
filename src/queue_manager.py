import threading
from typing import Optional

class MockRedis:
    def __init__(self):
        self._queue = []
        self._visited = set()
        self._lock = threading.Lock()

    def lpush(self, key: str, value: str):
        with self._lock:
            self._queue.insert(0, value)

    def rpop(self, key: str) -> Optional[str]:
        with self._lock:
            if self._queue:
                return self._queue.pop()
            return None

    def sadd(self, key: str, value: str) -> int:
        with self._lock:
            if value in self._visited:
                return 0
            self._visited.add(value)
            return 1

class DistributedQueueManager:
    QUEUE_KEY = "crawler:task:queue"
    DUPE_SET_KEY = "crawler:task:visited"

    def __init__(self, backend):
        self.db = backend

    def push_task(self, url: str) -> bool:
        if self.db.sadd(self.DUPE_SET_KEY, url) == 1:
            self.db.lpush(self.QUEUE_KEY, url)
            return True
        return False

    def pop_task(self) -> Optional[str]:
        task = self.db.rpop(self.QUEUE_KEY)
        if task:
            return task.decode('utf-8') if isinstance(task, bytes) else task
        return None
