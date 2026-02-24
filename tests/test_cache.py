"""Tests for cache module."""

from unittest.mock import patch

from cache import TTLCache


class TestTTLCache:
    """Test TTL cache get/set/eviction behavior."""

    def test_set_and_get(self) -> None:
        cache = TTLCache(ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key_returns_none(self) -> None:
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self) -> None:
        cache = TTLCache(ttl_seconds=5)
        with patch("cache.time.monotonic", return_value=1000.0):
            cache.set("key1", "value1")
        with patch("cache.time.monotonic", return_value=1006.0):
            assert cache.get("key1") is None

    def test_entry_within_ttl_returns_value(self) -> None:
        cache = TTLCache(ttl_seconds=10)
        with patch("cache.time.monotonic", return_value=1000.0):
            cache.set("key1", "value1")
        with patch("cache.time.monotonic", return_value=1009.0):
            assert cache.get("key1") == "value1"

    def test_eviction_removes_only_expired(self) -> None:
        cache = TTLCache(ttl_seconds=10)
        with patch("cache.time.monotonic", return_value=1000.0):
            cache.set("old", "old_val")
        with patch("cache.time.monotonic", return_value=1008.0):
            cache.set("new", "new_val")
        with patch("cache.time.monotonic", return_value=1011.0):
            assert cache.get("old") is None
            assert cache.get("new") == "new_val"

    def test_len_excludes_expired(self) -> None:
        cache = TTLCache(ttl_seconds=5)
        with patch("cache.time.monotonic", return_value=1000.0):
            cache.set("a", 1)
            cache.set("b", 2)
        with patch("cache.time.monotonic", return_value=1006.0):
            assert len(cache) == 0

    def test_overwrite_resets_ttl(self) -> None:
        cache = TTLCache(ttl_seconds=10)
        with patch("cache.time.monotonic", return_value=1000.0):
            cache.set("key", "v1")
        with patch("cache.time.monotonic", return_value=1008.0):
            cache.set("key", "v2")
        with patch("cache.time.monotonic", return_value=1015.0):
            assert cache.get("key") == "v2"

    def test_stores_complex_objects(self) -> None:
        cache = TTLCache()
        obj = {"nested": [1, 2, 3], "flag": True}
        cache.set("complex", obj)
        assert cache.get("complex") == obj
