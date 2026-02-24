"""YouTube search via yt-dlp ytsearch extractor."""

from __future__ import annotations

import asyncio
from typing import Optional

from cache import TTLCache
from config import load_config
from models import SearchResult

_cache = TTLCache()


class SearchError(Exception):
    """Search operation failed."""


def _validate_search_params(query: str, max_results: int) -> None:
    """Validate search input parameters."""
    if not isinstance(query, str) or not query.strip():
        raise SearchError("Search query must be a non-empty string")
    if not isinstance(max_results, int) or max_results < 1 or max_results > 20:
        raise SearchError("max_results must be an integer between 1 and 20")


def _sync_search(query: str, max_results: int) -> list[dict]:
    """Run yt-dlp ytsearch synchronously."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "socket_timeout": 30,
        **load_config(),
    }
    search_query = f"ytsearch{max_results}:{query}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if info is None:
                return []
            return info.get("entries") or []
    except yt_dlp.utils.DownloadError as exc:
        raise SearchError(str(exc)) from exc


def _build_search_result(entry: dict) -> Optional[SearchResult]:
    """Convert a yt-dlp search entry to a SearchResult."""
    video_id = entry.get("id")
    title = entry.get("title")
    if not video_id or not title:
        return None
    duration = entry.get("duration")
    return SearchResult(
        video_id=video_id,
        title=title,
        url=entry.get("url") or f"https://www.youtube.com/watch?v={video_id}",
        duration_seconds=int(duration) if duration else None,
        channel=entry.get("uploader") or entry.get("channel"),
        view_count=entry.get("view_count"),
        thumbnail_url=entry.get("thumbnail"),
        upload_date=entry.get("upload_date"),
    )


async def search_videos(query: str, max_results: int = 5) -> list[SearchResult]:
    """Async entry point: search YouTube videos.

    Args:
        query: Search query string.
        max_results: Number of results (1-20, default 5).

    Returns:
        List of SearchResult objects.
    """
    _validate_search_params(query, max_results)

    cache_key = f"search:{query.strip().lower()}:{max_results}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    entries = await asyncio.to_thread(_sync_search, query.strip(), max_results)
    results = []
    for entry in entries:
        sr = _build_search_result(entry)
        if sr is not None:
            results.append(sr)

    _cache.set(cache_key, results)
    return results
