"""Tests for validators module (thin delegation layer)."""

from __future__ import annotations

import pytest

from platforms import Platform
from validators import InvalidURLError, validate_url


class TestValidateUrl:

    def test_youtube_returns_canonical(self) -> None:
        result = validate_url("https://youtu.be/dQw4w9WgXcQ")
        assert result.platform == Platform.YOUTUBE
        assert result.canonical_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert result.video_id == "dQw4w9WgXcQ"

    def test_tiktok_full_url(self) -> None:
        result = validate_url("https://www.tiktok.com/@user/video/7234567890123456789")
        assert result.platform == Platform.TIKTOK
        assert result.video_id == "7234567890123456789"

    def test_tiktok_short_url(self) -> None:
        result = validate_url("https://vm.tiktok.com/ZMrABC123")
        assert result.platform == Platform.TIKTOK
        assert result.video_id is None

    def test_douyin_full_url(self) -> None:
        result = validate_url("https://www.douyin.com/video/7234567890123456789")
        assert result.platform == Platform.DOUYIN
        assert result.video_id == "7234567890123456789"

    def test_douyin_short_url(self) -> None:
        result = validate_url("https://v.douyin.com/iRNBho5p")
        assert result.platform == Platform.DOUYIN
        assert result.video_id is None

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_url("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_url("   ")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_url(None)  # type: ignore[arg-type]

    def test_non_string_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_url(12345)  # type: ignore[arg-type]

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_url("https://www.google.com")
