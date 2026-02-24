"""TTL cache with 10-minute expiry for video metadata."""

from __future__ import annotations

import threading
import time
from typing import Any, Optional

DEFAULT_TTL_SECONDS = 600  # 10 minutes


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL expiration."""

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if within TTL, else None."""
        with self._lock:
            self._evict_expired()
            entry = self._store.get(key)
            if entry is None:
                return None
            return entry[1]

    def set(self, key: str, value: Any) -> None:
        """Store a value with the current timestamp."""
        with self._lock:
            self._store[key] = (time.monotonic(), value)

    def _evict_expired(self) -> None:
        """Remove entries older than TTL. Must be called under lock."""
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._store.items() if now - ts >= self._ttl]
        for k in expired:
            del self._store[k]

    def __len__(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._store)
