"""Tests for batch.py — playlist info and parallel multi-URL extraction."""

import asyncio

import pytest
from unittest.mock import patch

from batch import (
    extract_playlist_info,
    batch_get_info,
    BatchError,
    PlaylistInfo,
    BatchResult,
    _cache,
)
from models import VideoInfo


# ---------------------------------------------------------------------------
# Playlist tests
# ---------------------------------------------------------------------------

SAMPLE_PLAYLIST_INFO = {
    "id": "PLtest123",
    "title": "Test Playlist",
    "uploader": "TestChannel",
    "playlist_count": 3,
    "entries": [
        {"id": "v1", "title": "Video 1", "duration": 60, "uploader": "Ch1"},
        {"id": "v2", "title": "Video 2", "duration": 120, "uploader": "Ch2"},
        {"id": "v3", "title": "Video 3", "duration": 180, "channel": "Ch3"},
    ],
}


class TestExtractPlaylistInfo:

    def setup_method(self):
        _cache._store.clear()

    def test_returns_playlist_info(self):
        with patch("batch._sync_extract_playlist", return_value=SAMPLE_PLAYLIST_INFO):
            result = asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLtest123")
            )
        assert isinstance(result, PlaylistInfo)
        assert result.title == "Test Playlist"
        assert result.playlist_id == "PLtest123"
        assert result.channel == "TestChannel"
        assert len(result.videos) == 3
        assert result.videos[0]["video_id"] == "v1"

    def test_respects_max_videos(self):
        with patch("batch._sync_extract_playlist", return_value=SAMPLE_PLAYLIST_INFO):
            result = asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLtest123", max_videos=2)
            )
        assert len(result.videos) == 2

    def test_cache_hit(self):
        with patch("batch._sync_extract_playlist", return_value=SAMPLE_PLAYLIST_INFO) as mock:
            asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLcache", max_videos=20)
            )
            asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLcache", max_videos=20)
            )
        assert mock.call_count == 1

    def test_invalid_max_videos_raises(self):
        with pytest.raises(BatchError, match="between 1 and 50"):
            asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PL1", max_videos=0)
            )

    def test_max_videos_too_high_raises(self):
        with pytest.raises(BatchError, match="between 1 and 50"):
            asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PL1", max_videos=51)
            )

    def test_skips_entries_without_id(self):
        info = {**SAMPLE_PLAYLIST_INFO, "entries": [{"title": "No ID"}, {"id": "v1", "title": "Good"}]}
        with patch("batch._sync_extract_playlist", return_value=info):
            result = asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLskip")
            )
        assert len(result.videos) == 1

    def test_to_dict(self):
        with patch("batch._sync_extract_playlist", return_value=SAMPLE_PLAYLIST_INFO):
            result = asyncio.get_event_loop().run_until_complete(
                extract_playlist_info("https://youtube.com/playlist?list=PLdict")
            )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "videos" in d


# ---------------------------------------------------------------------------
# Batch multi-URL tests
# ---------------------------------------------------------------------------

MOCK_VIDEO_INFO = VideoInfo(
    video_id="v1",
    title="Test",
    webpage_url="https://www.youtube.com/watch?v=v1",
    platform="youtube",
)


class TestBatchGetInfo:

    def test_all_succeed(self):
        async def mock_extract(url):
            return MOCK_VIDEO_INFO

        with patch("batch.extract_video_info", side_effect=mock_extract):
            result = asyncio.get_event_loop().run_until_complete(
                batch_get_info(["https://youtu.be/v1", "https://youtu.be/v2"])
            )
        assert isinstance(result, BatchResult)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0

    def test_partial_failure(self):
        async def mock_extract(url):
            if "bad" in url:
                raise Exception("fail")
            return MOCK_VIDEO_INFO

        with patch("batch.extract_video_info", side_effect=mock_extract):
            result = asyncio.get_event_loop().run_until_complete(
                batch_get_info(["https://youtu.be/v1", "https://bad.url"])
            )
        assert result.total == 2
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.results[1].success is False
        assert result.results[1].error is not None

    def test_empty_list_raises(self):
        with pytest.raises(BatchError, match="non-empty"):
            asyncio.get_event_loop().run_until_complete(
                batch_get_info([])
            )

    def test_not_list_raises(self):
        with pytest.raises(BatchError, match="non-empty"):
            asyncio.get_event_loop().run_until_complete(
                batch_get_info("not a list")
            )

    def test_exceeds_max_raises(self):
        urls = [f"https://youtu.be/v{i}" for i in range(11)]
        with pytest.raises(BatchError, match="Maximum 10"):
            asyncio.get_event_loop().run_until_complete(
                batch_get_info(urls)
            )

    def test_to_dict(self):
        async def mock_extract(url):
            return MOCK_VIDEO_INFO

        with patch("batch.extract_video_info", side_effect=mock_extract):
            result = asyncio.get_event_loop().run_until_complete(
                batch_get_info(["https://youtu.be/v1"])
            )
        d = result.to_dict()
        assert d["total"] == 1
        assert d["results"][0]["success"] is True
