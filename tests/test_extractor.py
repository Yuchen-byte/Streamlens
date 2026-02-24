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
    _extract_subtitle_summary,
    _process_info_dict,
    _select_formats,
    extract_video_info,
)
from models import VideoFormat, VideoInfo
from platforms import Platform, URLValidationResult


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
    "like_count": 15_000_000,
    "comment_count": 3_000_000,
    "upload_date": "20091025",
    "formats": SAMPLE_FORMATS,
    "automatic_captions": {},
    "requested_subtitles": None,
}

SAMPLE_TIKTOK_INFO = {
    "id": "7234567890123456789",
    "title": "Funny cat video",
    "webpage_url": "https://www.tiktok.com/@user/video/7234567890123456789",
    "uploader": "user",
    "duration": 30,
    "description": "Check out this funny cat! #cats #funny #viral",
    "thumbnail": "https://example.com/thumb.jpg",
    "view_count": 1_000_000,
    "like_count": 50_000,
    "comment_count": 1_200,
    "upload_date": "20240101",
    "formats": SAMPLE_FORMATS,
    "tags": ["cats", "funny", "viral"],
}

YT_VALIDATION = URLValidationResult(
    platform=Platform.YOUTUBE,
    canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ",
)

TIKTOK_VALIDATION = URLValidationResult(
    platform=Platform.TIKTOK,
    canonical_url="https://www.tiktok.com/@user/video/7234567890123456789",
    video_id="7234567890123456789",
)


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

    def test_produces_video_info_youtube(self) -> None:
        result = _process_info_dict(SAMPLE_INFO, Platform.YOUTUBE)
        assert isinstance(result, VideoInfo)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.platform == "youtube"
        assert result.title == "Rick Astley - Never Gonna Give You Up"
        assert result.duration_seconds == 212
        assert result.duration_string == "3:32"
        assert result.like_count == 15_000_000
        assert result.comment_count == 3_000_000
        assert result.best_quality_video is not None

    def test_produces_video_info_tiktok(self) -> None:
        result = _process_info_dict(SAMPLE_TIKTOK_INFO, Platform.TIKTOK)
        assert result.platform == "tiktok"
        assert result.video_id == "7234567890123456789"
        assert result.like_count == 50_000
        assert result.comment_count == 1_200

    def test_to_dict(self) -> None:
        result = _process_info_dict(SAMPLE_INFO, Platform.YOUTUBE)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["video_id"] == "dQw4w9WgXcQ"
        assert d["platform"] == "youtube"


class TestExtractSubtitleSummary:

    def test_youtube_auto_captions(self) -> None:
        info = {"automatic_captions": {"en": [{"data": "Hello world subtitle text here"}]}}
        result = _extract_subtitle_summary(info, Platform.YOUTUBE)
        assert result == "Hello world subtitle text here"

    def test_youtube_no_subtitles(self) -> None:
        info = {"automatic_captions": {}, "requested_subtitles": None}
        assert _extract_subtitle_summary(info, Platform.YOUTUBE) is None

    def test_tiktok_uses_tags(self) -> None:
        info = {"tags": ["cats", "funny", "viral", "trending"]}
        result = _extract_subtitle_summary(info, Platform.TIKTOK)
        assert result == "cats, funny, viral, trending"

    def test_tiktok_falls_back_to_description(self) -> None:
        info = {"tags": [], "description": "This is a great video about cooking tips"}
        result = _extract_subtitle_summary(info, Platform.TIKTOK)
        assert "cooking tips" in result

    def test_douyin_uses_tags(self) -> None:
        info = {"tags": ["搞笑视频", "猫咪日常", "生活记录"]}
        result = _extract_subtitle_summary(info, Platform.DOUYIN)
        assert "搞笑视频" in result


class TestExtractVideoInfo:

    @pytest.fixture(autouse=True)
    def _clear_cache(self) -> None:
        extractor._cache._store.clear()

    def test_returns_video_info_youtube(self) -> None:
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch("extractor._sync_extract", return_value=SAMPLE_INFO):
                result = asyncio.get_event_loop().run_until_complete(
                    extract_video_info("https://youtu.be/dQw4w9WgXcQ")
                )
        assert isinstance(result, VideoInfo)
        assert result.video_id == "dQw4w9WgXcQ"
        assert result.platform == "youtube"

    def test_returns_video_info_tiktok(self) -> None:
        with patch("extractor.validate_url", return_value=TIKTOK_VALIDATION):
            with patch("extractor._sync_extract", return_value=SAMPLE_TIKTOK_INFO):
                result = asyncio.get_event_loop().run_until_complete(
                    extract_video_info("https://www.tiktok.com/@user/video/7234567890123456789")
                )
        assert isinstance(result, VideoInfo)
        assert result.platform == "tiktok"
        assert result.video_id == "7234567890123456789"

    def test_cache_hit(self) -> None:
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
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
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch(
                "extractor._sync_extract",
                side_effect=GeoRestrictionError("geo blocked"),
            ):
                with pytest.raises(GeoRestrictionError):
                    asyncio.get_event_loop().run_until_complete(
                        extract_video_info("https://youtu.be/dQw4w9WgXcQ")
                    )

    def test_unavailable_error(self) -> None:
        with patch("extractor.validate_url", return_value=YT_VALIDATION):
            with patch(
                "extractor._sync_extract",
                side_effect=VideoUnavailableError("private video"),
            ):
                with pytest.raises(VideoUnavailableError):
                    asyncio.get_event_loop().run_until_complete(
                        extract_video_info("https://youtu.be/dQw4w9WgXcQ")
                    )


class TestSyncExtractSSHRouting:
    """Verify _sync_extract routes to SSH when ssh_host is configured."""

    def test_ssh_host_set_routes_to_ssh_extract(self) -> None:
        with patch("extractor.load_ssh_config", return_value="user@mac.local"):
            with patch("ssh.ssh_extract", return_value=SAMPLE_INFO) as mock_ssh:
                result = extractor._sync_extract(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    Platform.YOUTUBE,
                )
        assert result["id"] == "dQw4w9WgXcQ"
        mock_ssh.assert_called_once()

    def test_no_ssh_host_uses_local_ytdlp(self) -> None:
        with patch("extractor.load_ssh_config", return_value=None):
            with patch("extractor.load_config", return_value={}):
                mock_ydl = MagicMock()
                mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
                mock_ydl.__exit__ = MagicMock(return_value=False)
                mock_ydl.extract_info.return_value = SAMPLE_INFO
                with patch("yt_dlp.YoutubeDL", return_value=mock_ydl):
                    result = extractor._sync_extract(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        Platform.YOUTUBE,
                    )
        assert result["id"] == "dQw4w9WgXcQ"

    def test_ssh_error_with_geo_raises_geo_restriction(self) -> None:
        from ssh import SSHError
        with patch("extractor.load_ssh_config", return_value="user@mac.local"):
            with patch("ssh.ssh_extract", side_effect=SSHError("geo blocked")):
                with pytest.raises(GeoRestrictionError):
                    extractor._sync_extract(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        Platform.YOUTUBE,
                    )

    def test_ssh_error_generic_raises_extraction_error(self) -> None:
        from ssh import SSHError
        with patch("extractor.load_ssh_config", return_value="user@mac.local"):
            with patch("ssh.ssh_extract", side_effect=SSHError("Connection refused")):
                with pytest.raises(ExtractionError):
                    extractor._sync_extract(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        Platform.YOUTUBE,
                    )