"""Platform enum, URL pattern registry, and platform detection."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Optional

class InvalidURLError(Exception):
    """Raised when a URL is not a valid video URL for any supported platform."""


class Platform(enum.Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    DOUYIN = "douyin"


@dataclass(frozen=True)
class URLValidationResult:
    platform: Platform
    canonical_url: str
    video_id: Optional[str] = None


# (Platform, compiled regex, has_id capture group)
_PLATFORM_PATTERNS: tuple[tuple[Platform, re.Pattern[str], bool], ...] = (
    # YouTube
    (Platform.YOUTUBE, re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=(?P<id>[a-zA-Z0-9_-]{11})"
    ), True),
    (Platform.YOUTUBE, re.compile(
        r"(?:https?://)?youtu\.be/(?P<id>[a-zA-Z0-9_-]{11})"
    ), True),
    (Platform.YOUTUBE, re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/(?P<id>[a-zA-Z0-9_-]{11})"
    ), True),
    (Platform.YOUTUBE, re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/(?P<id>[a-zA-Z0-9_-]{11})"
    ), True),
    (Platform.YOUTUBE, re.compile(
        r"(?:https?://)?m\.youtube\.com/watch\?.*v=(?P<id>[a-zA-Z0-9_-]{11})"
    ), True),
    # TikTok
    (Platform.TIKTOK, re.compile(
        r"(?:https?://)?(?:www\.)?tiktok\.com/@[^/]+/video/(?P<id>\d+)"
    ), True),
    (Platform.TIKTOK, re.compile(
        r"(?:https?://)?vm\.tiktok\.com/[a-zA-Z0-9]+"
    ), False),
    # Douyin
    (Platform.DOUYIN, re.compile(
        r"(?:https?://)?(?:www\.)?douyin\.com/video/(?P<id>\d+)"
    ), True),
    (Platform.DOUYIN, re.compile(
        r"(?:https?://)?(?:www\.)?douyin\.com/user/[^?]+\?.*modal_id=(?P<id>\d+)"
    ), True),
    (Platform.DOUYIN, re.compile(
        r"(?:https?://)?v\.douyin\.com/[a-zA-Z0-9]+"
    ), False),
)


def detect_platform(url: str) -> URLValidationResult:
    """Detect platform from URL and return validation result.

    Raises:
        InvalidURLError: If the URL does not match any supported platform.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidURLError("URL must be a non-empty string")

    stripped = url.strip()
    for platform, pattern, has_id in _PLATFORM_PATTERNS:
        match = pattern.search(stripped)
        if match:
            video_id = match.group("id") if has_id else None
            if platform == Platform.YOUTUBE:
                canonical = f"https://www.youtube.com/watch?v={video_id}"
            elif platform == Platform.DOUYIN and video_id:
                canonical = f"https://www.douyin.com/video/{video_id}"
            else:
                canonical = stripped
            return URLValidationResult(
                platform=platform,
                canonical_url=canonical,
                video_id=video_id,
            )

    raise InvalidURLError(f"Unsupported or invalid URL: {stripped}")
