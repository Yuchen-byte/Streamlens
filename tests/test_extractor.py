"""Tests for extractor module (mocked yt-dlp)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

import extractor
from extractor import (
    ExtractionError,
    GeoRestrictionError,
    VideoUnavailableError,
    _build_format_entry,
    _process_info_dict,
    _select_formats,
    extract_video_info,
)
from models import VideoFormat, VideoInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FORMATS = [
    {
        "format_id": "18",
        "ext": "mp4",
        "height": 360,
        "width": 640,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "mp4a",
        "filesize": 5_000_000,
        "tbr": 500,
        "url": "https://example.com/360.mp4",
        "format_note": "360p",
    },
    {
        "format_id": "22",
        "ext": "mp4",
        "height": 720,
        "width": 1280,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "mp4a",
        "filesize": 15_000_000,
        "tbr": 1500,
        "url": "https://example.com/720.mp4",
        "format_note": "720p",
    },
    {
        "format_id": "140",
        "ext": "m4a",
        "vcodec": "none",
        "acodec": "mp4a",
        "abr": 128,
        "tbr": 128,
        "filesize": 2_000_000,
        "url": "https://example.com/audio.m4a",
        "format_note": "audio only",
    },
]

SAMPLE_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "uploader": "Rick Astley",
    "uploader_url": "https://www.youtube.com/@RickAstley",
    "duration": 212,
    "description": "The official video for...",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "view_count": 1_500_000_000,
    "upload_date": "20091025",
    "formats": SAMPLE_FORMATS,
    "automatic_captions": {},
    "requested_subtitles": None,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildFormatEntry:

    def test_valid_format(self) -> None:
        result = _build_format_entry(SAMPLE_FORMATS[0])
        assert isinstance(result, VideoFormat)
        assert result.format_id == "18"
        assert result.height == 360

    def test_missing_format_id_returns_none(self) -> None:
        assert _build_format_entry({"ext": "mp4"}) is None

    def test_missing_ext_returns_none(self) -> None:
        assert _build_format_entry({"format_id": "18"}) is None


class TestSelectFormats:

    def test_picks_best_quality(self) -> None:
        best, _, _ = _select_formats(SAMPLE_FORMATS)
        assert best is not None
        assert best.height == 720

    def test_picks_smallest(self) -> None:
        _, smallest, _ = _select_formats(SAMPLE_FORMATS)
        assert smallest is not None
        assert smallest.height == 360

    def test_picks_audio_only(self) -> None:
        _, _, audio = _select_formats(SAMPLE_FORMATS)
        assert audio is not None
        assert audio.ext == "m4a"

    def test_empty_formats(self) -> None:
        best, smallest, audio = _select_formats([])
        assert best is None
        assert smallest is None
        assert audio is None


class TestProcessInfoDict:

    def test_produces_video_info(self) -> None:
        result = _process_info_dict(SAMPLE_INFO)
        assert isinstance(result, VideoInfo)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.title == "Rick Astley - Never Gonna Give You Up"
        assert result.duration_seconds == 212
        assert result.duration_string == "3:32"
        assert result.best_quality_video is not None
        assert result.smallest_video is not None
        assert result.audio_only is not None

    def test_to_dict(self) -> None:
        result = _process_info_dict(SAMPLE_INFO)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["video_id"] == "dQw4w9WgXcQ"


class TestExtractVideoInfo:

    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        extractor._cache._store.clear()

    def test_returns_video_info(self) -> None:
        with patch("extractor._sync_extract", return_value=SAMPLE_INFO):
            result = asyncio.get_event_loop().run_until_complete(
                extract_video_info("https://youtu.be/dQw4w9WgXcQ")
            )
        assert isinstance(result, VideoInfo)
        assert result.video_id == "dQw4w9WgXcQ"

    def test_cache_hit(self) -> None:
        with patch("extractor._sync_extract", return_value=SAMPLE_INFO) as mock:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                extract_video_info("https://youtu.be/dQw4w9WgXcQ")
            )
            loop.run_until_complete(
                extract_video_info("https://youtu.be/dQw4w9WgXcQ")
            )
            assert mock.call_count == 1

    def test_geo_restriction_error(self) -> None:
        with patch(
            "extractor._sync_extract",
            side_effect=GeoRestrictionError("geo blocked"),
        ):
            with pytest.raises(GeoRestrictionError):
                asyncio.get_event_loop().run_until_complete(
                    extract_video_info("https://youtu.be/dQw4w9WgXcQ")
                )

    def test_unavailable_error(self) -> None:
        with patch(
            "extractor._sync_extract",
            side_effect=VideoUnavailableError("private video"),
        ):
            with pytest.raises(VideoUnavailableError):
                asyncio.get_event_loop().run_until_complete(
                    extract_video_info("https://youtu.be/dQw4w9WgXcQ")
                )
