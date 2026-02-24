"""Configuration loader — reads proxy and cookie settings from environment variables.

Supports per-platform overrides with global fallback:
    STREAMLENS_{PLATFORM}_{SUFFIX} → STREAMLENS_{SUFFIX} → empty
"""

from __future__ import annotations

import os
from typing import Optional


def _env(key: str, platform_key: Optional[str] = None) -> str:
    """Resolve an env var with optional platform-specific override.

    Checks STREAMLENS_{PLATFORM}_{SUFFIX} first, then STREAMLENS_{SUFFIX}.
    """
    if platform_key:
        val = os.environ.get(f"STREAMLENS_{platform_key}_{key}", "").strip()
        if val:
            return val
    return os.environ.get(f"STREAMLENS_{key}", "").strip()


def load_config(platform_key: Optional[str] = None) -> dict:
    """Build a yt-dlp options dict from environment variables.

    Args:
        platform_key: Optional platform identifier (e.g. "TIKTOK", "DOUYIN").
                      When set, platform-specific env vars take priority over global ones.

    Environment variables (global):
        STREAMLENS_PROXY         — proxy URL (e.g. http://127.0.0.1:7897)
        STREAMLENS_COOKIE_SOURCE — browser name (e.g. edge, chrome, firefox)
        STREAMLENS_COOKIE_FILE   — path to a Netscape cookies.txt file

    Platform-specific (e.g. for TIKTOK):
        STREAMLENS_TIKTOK_PROXY
        STREAMLENS_TIKTOK_COOKIE_SOURCE
        STREAMLENS_TIKTOK_COOKIE_FILE

    Priority: platform-specific > global; cookie_file > cookie_source.
    Only non-empty values are included in the returned dict.
    """
    opts: dict = {}

    proxy = _env("PROXY", platform_key)
    if proxy:
        opts["proxy"] = proxy

    cookie_file = _env("COOKIE_FILE", platform_key)
    cookie_source = _env("COOKIE_SOURCE", platform_key)

    if cookie_file:
        opts["cookiefile"] = cookie_file
    elif cookie_source:
        opts["cookiesfrombrowser"] = (cookie_source,)

    return opts


def load_ssh_config(platform_key: Optional[str] = None) -> Optional[str]:
    """Return the SSH host for remote yt-dlp execution, or None.

    Environment variables:
        STREAMLENS_SSH_HOST          — global (e.g. user@macbook.local)
        STREAMLENS_{PLATFORM}_SSH_HOST — per-platform override
    """
    host = _env("SSH_HOST", platform_key)
    return host if host else None
