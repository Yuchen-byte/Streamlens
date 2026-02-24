"""Batch operations — playlist info and parallel multi-URL extraction."""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Optional

from cache import TTLCache
from config import load_config
from extractor import (
    ExtractionError,
    extract_video_info,
    _sync_extract,
)
from models import VideoInfo
from platforms import Platform
from validators import validate_url, InvalidURLError

_cache = TTLCache()

_MAX_BATCH = 10
_CONCURRENCY = 3


class BatchError(Exception):
    """Batch operation failed."""


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

def _sync_extract_playlist(url: str, max_videos: int) -> dict:
    """Run yt-dlp to extract playlist metadata."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": max_videos,
        "socket_timeout": 30,
        **load_config(),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise BatchError(f"No info returned for {url}")
            return info
    except yt_dlp.utils.DownloadError as exc:
        raise BatchError(str(exc)) from exc


@dataclasses.dataclass(frozen=True)
class PlaylistInfo:
    """Playlist metadata with video list."""

    title: str
    playlist_id: str
    channel: Optional[str]
    video_count: Optional[int]
    videos: tuple[dict, ...]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


async def extract_playlist_info(url: str, max_videos: int = 20) -> PlaylistInfo:
    """Extract playlist metadata and video list.

    Args:
        url: Playlist URL.
        max_videos: Maximum number of videos to include (1-50, default 20).
    """
    if not isinstance(max_videos, int) or max_videos < 1 or max_videos > 50:
        raise BatchError("max_videos must be an integer between 1 and 50")

    cache_key = f"playlist:{url}:{max_videos}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    info = await asyncio.to_thread(_sync_extract_playlist, url, max_videos)
    entries = info.get("entries") or []

    videos = []
    for e in entries[:max_videos]:
        if not e or not e.get("id"):
            continue
        videos.append({
            "video_id": e.get("id", ""),
            "title": e.get("title", ""),
            "url": e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}",
            "duration_seconds": int(e["duration"]) if e.get("duration") else None,
            "channel": e.get("uploader") or e.get("channel"),
        })

    result = PlaylistInfo(
        title=info.get("title", ""),
        playlist_id=info.get("id", ""),
        channel=info.get("uploader") or info.get("channel"),
        video_count=info.get("playlist_count") or len(videos),
        videos=tuple(videos),
    )
    _cache.set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Batch multi-URL
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BatchResultItem:
    """Single item in a batch result — either success or error."""

    url: str
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BatchResult:
    """Aggregated batch extraction result."""

    total: int
    succeeded: int
    failed: int
    results: tuple[BatchResultItem, ...]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


async def _extract_one(url: str, semaphore: asyncio.Semaphore) -> BatchResultItem:
    """Extract info for a single URL with concurrency control."""
    async with semaphore:
        try:
            info = await extract_video_info(url)
            return BatchResultItem(
                url=url, success=True, data=info.to_dict()
            )
        except Exception as exc:
            return BatchResultItem(
                url=url, success=False, error=str(exc)
            )


async def batch_get_info(urls: list[str]) -> BatchResult:
    """Extract video info for multiple URLs in parallel.

    Args:
        urls: List of video URLs (max 10).

    Returns:
        BatchResult with per-URL success/error tracking.
    """
    if not isinstance(urls, list) or not urls:
        raise BatchError("urls must be a non-empty list")
    if len(urls) > _MAX_BATCH:
        raise BatchError(f"Maximum {_MAX_BATCH} URLs per batch")

    semaphore = asyncio.Semaphore(_CONCURRENCY)
    tasks = [_extract_one(url, semaphore) for url in urls]
    items = await asyncio.gather(*tasks)

    succeeded = sum(1 for i in items if i.success)
    return BatchResult(
        total=len(items),
        succeeded=succeeded,
        failed=len(items) - succeeded,
        results=tuple(items),
    )
