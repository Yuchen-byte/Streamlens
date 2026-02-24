"""Tests for validators module."""

import pytest

from validators import InvalidURLError, extract_video_id, validate_youtube_url


class TestExtractVideoId:
    """Test video ID extraction from various YouTube URL formats."""

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
    def test_valid_urls(self, url: str, expected_id: str) -> None:
        assert extract_video_id(url) == expected_id

    @pytest.mark.parametrize("url", [
        "https://www.google.com",
        "not a url",
        "",
        "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
        "https://www.youtube.com/watch?v=short",
    ])
    def test_invalid_urls(self, url: str) -> None:
        with pytest.raises(InvalidURLError):
            extract_video_id(url)


class TestValidateYoutubeUrl:
    """Test URL validation and canonicalization."""

    def test_returns_canonical_url(self) -> None:
        result = validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_youtube_url("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_youtube_url("   ")

    def test_none_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_youtube_url(None)  # type: ignore[arg-type]

    def test_non_string_raises(self) -> None:
        with pytest.raises(InvalidURLError):
            validate_youtube_url(12345)  # type: ignore[arg-type]
