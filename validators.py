"""URL validation — thin delegation layer over platforms module."""

from __future__ import annotations

from platforms import InvalidURLError, URLValidationResult, detect_platform

# Re-export InvalidURLError so existing imports (e.g. from validators import InvalidURLError) still work.
__all__ = ["InvalidURLError", "validate_url"]


def validate_url(url: str) -> URLValidationResult:
    """Validate a URL against all supported platforms.

    Returns a URLValidationResult with platform, canonical_url, and optional video_id.

    Raises:
        InvalidURLError: If the URL does not match any supported platform.
    """
    return detect_platform(url)
