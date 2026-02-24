"""yt-dlp wrapper with async bridge, format selection, and caching."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Optional

from cache import TTLCache
from config import load_config
from models import VideoFormat, VideoInfo
from validators import validate_youtube_url


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """General extraction failure."""


class GeoRestrictionError(ExtractionError):
    """Video is geo-restricted."""


class VideoUnavailableError(ExtractionError):
    """Video is private or unavailable."""


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_cache = TTLCache()

# ---------------------------------------------------------------------------
# yt-dlp installation check
# ---------------------------------------------------------------------------

def ensure_ytdlp_installed() -> None:
    """Auto-install yt-dlp if not importable."""
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


# ---------------------------------------------------------------------------
# Synchronous extraction
# ---------------------------------------------------------------------------

_YDL_OPTS = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 30,
    "writeautomaticsub": True,
    "subtitleslangs": ["en"],
}


def _sync_extract(url: str) -> dict:
    """Run yt-dlp synchronously and return the info dict."""
    import yt_dlp

    opts = {**_YDL_OPTS, **load_config()}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ExtractionError(f"No info returned for {url}")
            return info
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc).lower()
        if "geo" in msg:
            raise GeoRestrictionError(str(exc)) from exc
        if "private" in msg or "unavailable" in msg:
            raise VideoUnavailableError(str(exc)) from exc
        raise ExtractionError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------


def _build_format_entry(fmt: dict) -> Optional[VideoFormat]:
    """Convert a single yt-dlp format dict to a VideoFormat, or None."""
    format_id = fmt.get("format_id")
    ext = fmt.get("ext")
    if not format_id or not ext:
        return None
    resolution = fmt.get("resolution")
    if not resolution:
        w, h = fmt.get("width"), fmt.get("height")
        if w and h:
            resolution = f"{w}x{h}"
    return VideoFormat(
        format_id=format_id,
        ext=ext,
        resolution=resolution,
        height=fmt.get("height"),
        width=fmt.get("width"),
        fps=fmt.get("fps"),
        vcodec=fmt.get("vcodec"),
        acodec=fmt.get("acodec"),
        filesize=fmt.get("filesize"),
        tbr=fmt.get("tbr"),
        url=fmt.get("url"),
        format_note=fmt.get("format_note"),
    )


def _has_video(fmt: dict) -> bool:
    vcodec = fmt.get("vcodec", "none")
    return vcodec not in ("none", None)


def _has_audio(fmt: dict) -> bool:
    acodec = fmt.get("acodec", "none")
    return acodec not in ("none", None)


def _select_formats(
    formats: list[dict],
) -> tuple[Optional[VideoFormat], Optional[VideoFormat], Optional[VideoFormat]]:
    """Pick best_quality_video, smallest_video, and audio_only from formats."""
    video_fmts = [f for f in formats if _has_video(f)]
    audio_only_fmts = [f for f in formats if _has_audio(f) and not _has_video(f)]

    # best_quality_video: highest height
    best = None
    for f in video_fmts:
        h = f.get("height") or 0
        if best is None or h > (best.get("height") or 0):
            best = f

    # smallest_video: lowest filesize, fallback to lowest tbr
    smallest = None
    for f in video_fmts:
        f_size = f.get("filesize") or f.get("tbr") or float("inf")
        s_size = (
            (smallest.get("filesize") or smallest.get("tbr") or float("inf"))
            if smallest
            else float("inf")
        )
        if f_size < s_size:
            smallest = f

    # audio_only: highest abr
    best_audio = None
    for f in audio_only_fmts:
        abr = f.get("abr") or f.get("tbr") or 0
        best_abr = (
            (best_audio.get("abr") or best_audio.get("tbr") or 0)
            if best_audio
            else 0
        )
        if abr > best_abr:
            best_audio = f

    return (
        _build_format_entry(best) if best else None,
        _build_format_entry(smallest) if smallest else None,
        _build_format_entry(best_audio) if best_audio else None,
    )


def _extract_subtitle_summary(info: dict) -> Optional[str]:
    """Extract first 2000 chars of auto-subtitles if available."""
    auto_subs = info.get("automatic_captions") or {}
    for lang in ("en", "en-orig"):
        entries = auto_subs.get(lang, [])
        for entry in entries:
            data = entry.get("data") or entry.get("url")
            if isinstance(data, str) and len(data) > 10:
                return data[:2000]
    # Fallback: check requested_subtitles
    req_subs = info.get("requested_subtitles") or {}
    for lang_data in req_subs.values():
        if isinstance(lang_data, dict):
            data = lang_data.get("data")
            if isinstance(data, str) and len(data) > 10:
                return data[:2000]
    return None


def _format_duration(seconds: Optional[int]) -> Optional[str]:
    """Convert seconds to M:SS or H:MM:SS string."""
    if seconds is None:
        return None
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _process_info_dict(info: dict) -> VideoInfo:
    """Transform raw yt-dlp info dict into an immutable VideoInfo."""
    formats = info.get("formats") or []
    best_quality, smallest, audio_only = _select_formats(formats)
    duration = info.get("duration")

    return VideoInfo(
        video_id=info.get("id", ""),
        title=info.get("title", ""),
        webpage_url=info.get("webpage_url", ""),
        uploader=info.get("uploader"),
        uploader_url=info.get("uploader_url"),
        duration_seconds=int(duration) if duration else None,
        duration_string=_format_duration(int(duration) if duration else None),
        description=info.get("description"),
        thumbnail_url=info.get("thumbnail"),
        view_count=info.get("view_count"),
        upload_date=info.get("upload_date"),
        best_quality_video=best_quality,
        smallest_video=smallest,
        audio_only=audio_only,
        subtitles_summary=_extract_subtitle_summary(info),
    )


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------


async def extract_video_info(url: str) -> VideoInfo:
    """Async entry point: validate, check cache, extract, cache result."""
    canonical_url = validate_youtube_url(url)

    cached = _cache.get(canonical_url)
    if cached is not None:
        return cached

    info = await asyncio.to_thread(_sync_extract, canonical_url)
    result = _process_info_dict(info)
    _cache.set(canonical_url, result)
    return result
