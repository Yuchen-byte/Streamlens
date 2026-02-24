"""Tests for platform detection module."""

from __future__ import annotations

import pytest

from platforms import Platform, URLValidationResult, detect_platform
from validators import InvalidURLError


class TestDetectPlatformYouTube:

    @pytest.mark.parametrize("url,expected_id", [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("http://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
        ("  https://youtu.be/dQw4w9WgXcQ  ", "dQw4w9WgXcQ"),
    ])
    def test_youtube_urls(self, url: str, expected_id: str) -> None:
        result = detect_platform(url)
        assert result.platform == Platform.YOUTUBE
        assert result.video_id == expected_id
        assert result.canonical_url == f"https://www.youtube.com/watch?v={expected_id}"


class TestDetectPlatformTikTok:

    @pytest.mark.parametrize("url", [
        "https://www.tiktok.com/@user/video/7234567890123456789",
        "https://tiktok.com/@some.user/video/7234567890123456789",
        "http://www.tiktok.com/@user/video/7234567890123456789",
    ])
    def test_tiktok_full_urls(self, url: str) -> None:
        result = detect_platform(url)
        assert result.platform == Platform.TIKTOK
        assert result.video_id == "7234567890123456789"

    def test_tiktok_short_url(self) -> None:
        result = detect_platform("https://vm.tiktok.com/ZMrABC123")
        assert result.platform == Platform.TIKTOK
        assert result.video_id is None
        assert result.canonical_url == "https://vm.tiktok.com/ZMrABC123"


class TestDetectPlatformDouyin:

    @pytest.mark.parametrize("url", [
        "https://www.douyin.com/video/7234567890123456789",
        "https://douyin.com/video/7234567890123456789",
        "http://www.douyin.com/video/7234567890123456789",
    ])
    def test_douyin_full_urls(self, url: str) -> None:
        result = detect_platform(url)
        assert result.platform == Platform.DOUYIN
        assert result.video_id == "7234567890123456789"

    def test_douyin_short_url(self) -> None:
        result = detect_platform("https://v.douyin.com/iRNBho5p")
        assert result.platform == Platform.DOUYIN
        assert result.video_id is None
        assert result.canonical_url == "https://v.douyin.com/iRNBho5p"

    @pytest.mark.parametrize("url,expected_id", [
        (
            "https://www.douyin.com/user/self?from_tab_name=main&modal_id=7609331978659515499&showTab=like",
            "7609331978659515499",
        ),
        (
            "https://www.douyin.com/user/MS4wLjABxxx?modal_id=7609331978659515499",
            "7609331978659515499",
        ),
        (
            "https://douyin.com/user/self?modal_id=1234567890123456789",
            "1234567890123456789",
        ),
    ])
    def test_douyin_user_modal_id_urls(self, url: str, expected_id: str) -> None:
        result = detect_platform(url)
        assert result.platform == Platform.DOUYIN
        assert result.video_id == expected_id
        assert result.canonical_url == f"https://www.douyin.com/video/{expected_id}"


class TestDetectPlatformInvalid:

    @pytest.mark.parametrize("url", [
        "https://www.google.com",
        "not a url",
        "https://www.youtube.com/playlist?list=PLrAXtmErZgOe",
        "https://www.youtube.com/watch?v=short",
    ])
    def test_invalid_urls(self, url: str) -> None:
        with pytest.raises(InvalidURLError):
            detect_platform(url)

    def test_empty_string(self) -> None:
        with pytest.raises(InvalidURLError):
            detect_platform("")

    def test_whitespace_only(self) -> None:
        with pytest.raises(InvalidURLError):
            detect_platform("   ")

    def test_none(self) -> None:
        with pytest.raises(InvalidURLError):
            detect_platform(None)  # type: ignore[arg-type]

    def test_non_string(self) -> None:
        with pytest.raises(InvalidURLError):
            detect_platform(12345)  # type: ignore[arg-type]
