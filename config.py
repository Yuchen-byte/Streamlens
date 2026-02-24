"""Configuration loader — reads proxy and cookie settings from environment variables."""

from __future__ import annotations

import os


def load_config() -> dict:
    """Build a yt-dlp options dict from environment variables.

    Environment variables:
        STREAMLENS_PROXY         — proxy URL (e.g. http://127.0.0.1:7897)
        STREAMLENS_COOKIE_SOURCE — browser name (e.g. edge, chrome, firefox)
        STREAMLENS_COOKIE_FILE   — path to a Netscape cookies.txt file

    Priority: STREAMLENS_COOKIE_FILE > STREAMLENS_COOKIE_SOURCE > no cookie.
    Only non-empty values are included in the returned dict.
    """
    opts: dict = {}

    proxy = os.environ.get("STREAMLENS_PROXY", "").strip()
    if proxy:
        opts["proxy"] = proxy

    cookie_file = os.environ.get("STREAMLENS_COOKIE_FILE", "").strip()
    cookie_source = os.environ.get("STREAMLENS_COOKIE_SOURCE", "").strip()

    if cookie_file:
        opts["cookiefile"] = cookie_file
    elif cookie_source:
        opts["cookiesfrombrowser"] = (cookie_source,)

    return opts
