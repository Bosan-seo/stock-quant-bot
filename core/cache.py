"""
Thread-safe in-memory TTL (Time-To-Live) Cache implementation.
Zero external dependencies, ideal for memory-constrained environments (GCP e2-micro 1GB RAM).
Provides automatic expiration for market indices, stock data, and AI responses.
"""
import time
import threading
from typing import Any, Optional, Dict, Tuple


class SimpleTTLCache:
    """Thread-safe key-value cache with automatic expiration."""

    def __init__(self, default_ttl: int = 300, max_items: int = 200):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._max_items = max_items
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get item if not expired, else None."""
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item with TTL in seconds."""
        expiry = time.time() + (ttl if ttl is not None else self._default_ttl)
        with self._lock:
            # Simple eviction if cache exceeds max_items
            if len(self._cache) >= self._max_items:
                # Remove oldest expired or just first item
                now = time.time()
                expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
                for k in expired_keys:
                    del self._cache[k]
                if len(self._cache) >= self._max_items:
                    # Pop first key
                    first_key = next(iter(self._cache))
                    del self._cache[first_key]
            self._cache[key] = (value, expiry)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._cache.clear()


# Global cache instances
# 1. Macro & Market Indices: TTL 5 mins (300s)
market_cache = SimpleTTLCache(default_ttl=300, max_items=50)

# 2. Stock Data & Fundamentals: TTL 3 mins (180s)
stock_cache = SimpleTTLCache(default_ttl=180, max_items=100)

# 3. AI Diagnoses: TTL 10 mins (600s)
ai_cache = SimpleTTLCache(default_ttl=600, max_items=100)
