"""Tests for search.py — YouTube search via yt-dlp."""

import asyncio

import pytest
from unittest.mock import patch

from search import search_videos, _build_search_result, _validate_search_params, SearchError, _cache
from models import SearchResult


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestValidateSearchParams:

    def test_valid_params(self):
        _validate_search_params("python tutorial", 5)

    def test_empty_query_raises(self):
        with pytest.raises(SearchError, match="non-empty"):
            _validate_search_params("", 5)

    def test_whitespace_query_raises(self):
        with pytest.raises(SearchError, match="non-empty"):
            _validate_search_params("   ", 5)

    def test_none_query_raises(self):
        with pytest.raises(SearchError, match="non-empty"):
            _validate_search_params(None, 5)

    def test_max_results_too_low(self):
        with pytest.raises(SearchError, match="between 1 and 20"):
            _validate_search_params("test", 0)

    def test_max_results_too_high(self):
        with pytest.raises(SearchError, match="between 1 and 20"):
            _validate_search_params("test", 21)

    def test_max_results_not_int(self):
        with pytest.raises(SearchError, match="between 1 and 20"):
            _validate_search_params("test", "5")


# ---------------------------------------------------------------------------
# Build search result tests
# ---------------------------------------------------------------------------

class TestBuildSearchResult:

    def test_valid_entry(self):
        entry = {
            "id": "abc123",
            "title": "Test Video",
            "url": "https://www.youtube.com/watch?v=abc123",
            "duration": 120,
            "uploader": "TestChannel",
            "view_count": 1000,
            "thumbnail": "https://i.ytimg.com/vi/abc123/default.jpg",
            "upload_date": "20240101",
        }
        result = _build_search_result(entry)
        assert isinstance(result, SearchResult)
        assert result.video_id == "abc123"
        assert result.title == "Test Video"
        assert result.duration_seconds == 120
        assert result.channel == "TestChannel"
        assert result.view_count == 1000

    def test_missing_id_returns_none(self):
        assert _build_search_result({"title": "No ID"}) is None

    def test_missing_title_returns_none(self):
        assert _build_search_result({"id": "abc123"}) is None

    def test_generates_url_from_id(self):
        entry = {"id": "xyz789", "title": "Test"}
        result = _build_search_result(entry)
        assert result.url == "https://www.youtube.com/watch?v=xyz789"

    def test_uses_channel_fallback(self):
        entry = {"id": "abc", "title": "T", "channel": "Ch1"}
        result = _build_search_result(entry)
        assert result.channel == "Ch1"


# ---------------------------------------------------------------------------
# Async search tests (mocked yt-dlp)
# ---------------------------------------------------------------------------

class TestSearchVideos:

    def setup_method(self):
        _cache._store.clear()

    def test_returns_results(self):
        mock_entries = [
            {"id": "v1", "title": "Video 1", "duration": 60, "uploader": "Ch1"},
            {"id": "v2", "title": "Video 2", "duration": 120, "uploader": "Ch2"},
        ]
        with patch("search._sync_search", return_value=mock_entries):
            results = asyncio.get_event_loop().run_until_complete(
                search_videos("test query", max_results=2)
            )
        assert len(results) == 2
        assert results[0].video_id == "v1"
        assert results[1].video_id == "v2"

    def test_cache_hit(self):
        mock_entries = [{"id": "v1", "title": "Video 1"}]
        with patch("search._sync_search", return_value=mock_entries) as mock:
            r1 = asyncio.get_event_loop().run_until_complete(
                search_videos("cached query", max_results=5)
            )
            r2 = asyncio.get_event_loop().run_until_complete(
                search_videos("cached query", max_results=5)
            )
        assert mock.call_count == 1
        assert len(r1) == len(r2)

    def test_skips_invalid_entries(self):
        mock_entries = [
            {"id": "v1", "title": "Good"},
            {"id": None, "title": "Bad"},
            {"title": "No ID"},
        ]
        with patch("search._sync_search", return_value=mock_entries):
            results = asyncio.get_event_loop().run_until_complete(
                search_videos("test skip", max_results=3)
            )
        assert len(results) == 1

    def test_empty_query_raises(self):
        with pytest.raises(SearchError):
            asyncio.get_event_loop().run_until_complete(
                search_videos("", max_results=5)
            )

    def test_empty_results(self):
        with patch("search._sync_search", return_value=[]):
            results = asyncio.get_event_loop().run_until_complete(
                search_videos("obscure query xyz", max_results=5)
            )
        assert results == []
