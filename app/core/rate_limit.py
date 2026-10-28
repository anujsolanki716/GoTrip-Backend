import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, window: int, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        return hits

    def hit(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, window, now)
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def is_blocked(self, key: str, limit: int, window: int) -> bool:
        with self._lock:
            return len(self._prune(key, window, time.monotonic())) >= limit

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


enquiry_limiter = SlidingWindowLimiter()
login_limiter = SlidingWindowLimiter()
