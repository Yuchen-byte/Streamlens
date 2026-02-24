"""Tests for audio stream URL extraction."""

import asyncio

import pytest
from unittest.mock import patch

from extractor import (
    _select_best_audio,
    extract_audio_url,
    ExtractionError,
    _cache,
)
from models import AudioStreamInfo
from platforms import Platform, URLValidationResult


YT_VALIDATION = URLValidationResult(
    platform=Platform.YOUTUBE,
    canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ",
)

SAMPLE_AUDIO_FORMATS = [
    {
        "format_id": "140",
        "ext": "m4a",
        "acodec": "mp4a.40.2",
        "vcodec": "none",
        "abr": 128.0,
        "filesize": 3000000,
        "url": "https://example.com/audio_m4a",
    },
    {
        "format_id": "251",
        "ext": "opus",
        "acodec": "opus",
        "vcodec": "none",
        "abr": 160.0,
        "filesize": 3500000,
        "url": "https://example.com/audio_opus",
    },
    {
        "format_id": "250",
        "ext": "opus",
        "acodec": "opus",
        "vcodec": "none",
        "abr": 70.0,
        "filesize": 1500000,
        "url": "https://example.com/audio_opus_low",
    },
    {
        "format_id": "18",
        "ext": "mp4",
        "acodec": "mp4a.40.2",
        "vcodec": "avc1.42001E",
        "height": 360,
        "abr": 96.0,
        "url": "https://example.com/video_mp4",
    },
]

SAMPLE_INFO = {
    "id": "dQw4w9WgXcQ",
    "title": "Test Video",
    "formats": SAMPLE_AUDIO_FORMATS,
}


class TestSelectBestAudio:

    def test_best_picks_highest_abr(self):
        result = _select_best_audio(SAMPLE_AUDIO_FORMATS, "best")
        assert result["format_id"] == "251"
        assert result["abr"] == 160.0

    def test_smallest_picks_lowest_filesize(self):
        result = _select_best_audio(SAMPLE_AUDIO_FORMATS, "smallest")
        assert result["format_id"] == "250"
        assert result["filesize"] == 1500000

    def test_excludes_video_formats(self):
        result = _select_best_audio(SAMPLE_AUDIO_FORMATS, "best")
        assert result["format_id"] != "18"

    def test_no_audio_formats_raises(self):
        video_only = [
            {"format_id": "18", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "url": "x"},
        ]
        with pytest.raises(ExtractionError, match="No audio-only"):
            _select_best_audio(video_only, "best")

    def test_empty_formats_raises(self):
        with pytest.raises(ExtractionError, match="No audio-only"):
            _select_best_audio([], "best")

    def test_prefers_m4a_at_same_bitrate(self):
        fmts = [
            {"format_id": "1", "ext": "ogg", "acodec": "vorbis", "vcodec": "none", "abr": 128.0, "url": "x"},
            {"format_id": "2", "ext": "m4a", "acodec": "aac", "vcodec": "none", "abr": 128.0, "url": "y"},
        ]
        result = _select_best_audio(fmts, "best")
        assert result["format_id"] == "2"


class TestExtractAudioUrl:

    def setup_method(self):
        _cache._store.clear()

    def test_returns_audio_stream_info(self):
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch("extractor._sync_extract", return_value=SAMPLE_INFO):
                result = asyncio.get_event_loop().run_until_complete(
                    extract_audio_url("https://youtu.be/dQw4w9WgXcQ")
                )
        assert isinstance(result, AudioStreamInfo)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.ext == "opus"
        assert result.abr == 160.0
        assert "example.com" in result.url

    def test_smallest_quality(self):
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch("extractor._sync_extract", return_value=SAMPLE_INFO):
                result = asyncio.get_event_loop().run_until_complete(
                    extract_audio_url("https://youtu.be/dQw4w9WgXcQ", quality="smallest")
                )
        assert result.filesize == 1500000

    def test_cache_hit(self):
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch("extractor._sync_extract", return_value=SAMPLE_INFO) as mock:
                asyncio.get_event_loop().run_until_complete(
                    extract_audio_url("https://youtu.be/dQw4w9WgXcQ")
                )
                asyncio.get_event_loop().run_until_complete(
                    extract_audio_url("https://youtu.be/dQw4w9WgXcQ")
                )
        assert mock.call_count == 1

    def test_invalid_quality_raises(self):
        with pytest.raises(ExtractionError, match="quality must be"):
            asyncio.get_event_loop().run_until_complete(
                extract_audio_url("https://youtu.be/dQw4w9WgXcQ", quality="medium")
            )
