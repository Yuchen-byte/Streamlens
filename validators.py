"""YouTube URL validation and video ID extraction."""

from __future__ import annotations

import re


class InvalidURLError(Exception):
    """Raised when a URL is not a valid YouTube video URL."""


YOUTUBE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=(?P<id>[a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?youtu\.be/(?P<id>[a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?m\.youtube\.com/watch\?.*v=(?P<id>[a-zA-Z0-9_-]{11})"),
)


def extract_video_id(url: str) -> str:
    """Extract the 11-character video ID from a YouTube URL.

    Raises:
        InvalidURLError: If the URL does not match any known YouTube pattern.
    """
    url = url.strip()
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group("id")
    raise InvalidURLError(f"Not a valid YouTube URL: {url}")


def validate_youtube_url(url: str) -> str:
    """Validate and sanitize a YouTube URL.

    Returns the canonical watch URL.

    Raises:
        InvalidURLError: If the URL is not a valid YouTube video URL.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidURLError("URL must be a non-empty string")
    video_id = extract_video_id(url)
    return f"https://www.youtube.com/watch?v={video_id}"
