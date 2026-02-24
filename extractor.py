"""yt-dlp wrapper with async bridge, format selection, and caching."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Optional

from cache import TTLCache
from config import load_config
from models import VideoFormat, VideoInfo, TranscriptSegment, TranscriptResult, AudioStreamInfo, TranscriptionResult
from platforms import Platform
from validators import validate_url
from transcript import parse_subtitles, segments_to_text


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    """General extraction failure."""


class GeoRestrictionError(ExtractionError):
    """Video is geo-restricted."""


class VideoUnavailableError(ExtractionError):
    """Video is private or unavailable."""


class TranscriptionError(ExtractionError):
    """Whisper transcription failure."""


def _map_error(msg: str) -> None:
    """Raise the appropriate ExtractionError subclass based on *msg*.

    Always raises — never returns normally.
    """
    lower = msg.lower()
    if "geo" in lower:
        raise GeoRestrictionError(msg)
    if "private" in lower or "unavailable" in lower:
        raise VideoUnavailableError(msg)
    raise ExtractionError(msg)


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
# yt-dlp options: base + per-platform overrides
# ---------------------------------------------------------------------------

_YDL_OPTS = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 30,
}

_PLATFORM_YDL_OVERRIDES: dict[Platform, dict] = {
    Platform.YOUTUBE: {
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
    },
    Platform.TIKTOK: {},
    Platform.DOUYIN: {},
}

_PLATFORM_CONFIG_KEY: dict[Platform, Optional[str]] = {
    Platform.YOUTUBE: None,
    Platform.TIKTOK: "TIKTOK",
    Platform.DOUYIN: "DOUYIN",
}


def _sync_extract(url: str, platform: Platform) -> dict:
    """Run yt-dlp synchronously and return the info dict."""
    overrides = _PLATFORM_YDL_OVERRIDES.get(platform, {})
    config_key = _PLATFORM_CONFIG_KEY.get(platform)
    opts = {**_YDL_OPTS, **overrides, **load_config(config_key)}

    import yt_dlp
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ExtractionError(f"No info returned for {url}")
            return info
    except yt_dlp.utils.DownloadError as exc:
        _map_error(str(exc))


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

    best = None
    for f in video_fmts:
        h = f.get("height") or 0
        if best is None or h > (best.get("height") or 0):
            best = f

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


def _extract_subtitle_summary(info: dict, platform: Platform) -> Optional[str]:
    """Extract subtitle/content summary based on platform."""
    if platform == Platform.YOUTUBE:
        auto_subs = info.get("automatic_captions") or {}
        for lang in ("en", "en-orig"):
            entries = auto_subs.get(lang, [])
            for entry in entries:
                data = entry.get("data") or entry.get("url")
                if isinstance(data, str) and len(data) > 10:
                    return data[:2000]
        req_subs = info.get("requested_subtitles") or {}
        for lang_data in req_subs.values():
            if isinstance(lang_data, dict):
                data = lang_data.get("data")
                if isinstance(data, str) and len(data) > 10:
                    return data[:2000]
        return None

    # TikTok / Douyin: try tags first, then description
    tags = info.get("tags")
    if tags and isinstance(tags, list):
        joined = ", ".join(str(t) for t in tags if t)
        if len(joined) > 10:
            return joined[:2000]
    desc = info.get("description")
    if isinstance(desc, str) and len(desc) > 10:
        return desc[:2000]
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


def _process_info_dict(info: dict, platform: Platform) -> VideoInfo:
    """Transform raw yt-dlp info dict into an immutable VideoInfo."""
    formats = info.get("formats") or []
    best_quality, smallest, audio_only = _select_formats(formats)
    duration = info.get("duration")

    return VideoInfo(
        video_id=info.get("id", ""),
        title=info.get("title", ""),
        webpage_url=info.get("webpage_url", ""),
        platform=platform.value,
        uploader=info.get("uploader"),
        uploader_url=info.get("uploader_url"),
        duration_seconds=int(duration) if duration else None,
        duration_string=_format_duration(int(duration) if duration else None),
        description=info.get("description"),
        thumbnail_url=info.get("thumbnail"),
        view_count=info.get("view_count"),
        like_count=info.get("like_count"),
        comment_count=info.get("comment_count"),
        upload_date=info.get("upload_date"),
        best_quality_video=best_quality,
        smallest_video=smallest,
        audio_only=audio_only,
        subtitles_summary=_extract_subtitle_summary(info, platform),
    )


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------


async def extract_video_info(url: str) -> VideoInfo:
    """Async entry point: validate, check cache, extract, cache result."""
    validation = validate_url(url)
    canonical_url = validation.canonical_url
    platform = validation.platform

    cached = _cache.get(canonical_url)
    if cached is not None:
        return cached

    info = await asyncio.to_thread(_sync_extract, canonical_url, platform)
    result = _process_info_dict(info, platform)
    _cache.set(canonical_url, result)
    return result


# ---------------------------------------------------------------------------
# Subtitle / transcript extraction
# ---------------------------------------------------------------------------

_SUBTITLE_YDL_OPTS = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 30,
    "writesubtitles": True,
    "writeautomaticsub": True,
}


def _find_best_subtitle(info: dict, lang: str) -> tuple[str, str, bool]:
    """Find the best subtitle data for the requested language.

    Returns (subtitle_data, actual_lang, is_auto_generated).
    Fallback chain: manual subs (exact lang) -> auto captions (exact lang)
                    -> manual subs (any) -> auto captions (any)
    Raises ExtractionError if no subtitles found.
    """
    manual_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    # Try exact language match first
    for source, is_auto in [(manual_subs, False), (auto_subs, True)]:
        for key in (lang, f"{lang}-orig"):
            entries = source.get(key, [])
            for entry in entries:
                data = entry.get("data")
                if isinstance(data, str) and len(data) > 10:
                    return data, key.split("-")[0], is_auto

    # Fallback: first available language
    for source, is_auto in [(manual_subs, False), (auto_subs, True)]:
        for key, entries in source.items():
            for entry in entries:
                data = entry.get("data")
                if isinstance(data, str) and len(data) > 10:
                    return data, key.split("-")[0], is_auto

    raise ExtractionError("No subtitles available for this video")


def _sync_extract_subtitles(url: str, platform: Platform, lang: str) -> dict:
    """Run yt-dlp to extract subtitle data."""
    config_key = _PLATFORM_CONFIG_KEY.get(platform)
    opts = {
        **_SUBTITLE_YDL_OPTS,
        "subtitleslangs": [lang, f"{lang}-orig"],
        **load_config(config_key),
    }

    import yt_dlp
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ExtractionError(f"No info returned for {url}")
            return info
    except yt_dlp.utils.DownloadError as exc:
        _map_error(str(exc))


async def extract_transcript(
    url: str, lang: str = "en", output_format: str = "text"
) -> TranscriptResult:
    """Async entry point: extract subtitles and return structured transcript.

    Args:
        url: Video URL.
        lang: Preferred subtitle language (default "en").
        output_format: "text" for plain text, "segments" for timestamped segments.

    Returns:
        TranscriptResult with parsed subtitle data.
    """
    validation = validate_url(url)
    canonical_url = validation.canonical_url
    platform = validation.platform
    video_id = validation.video_id or ""

    cache_key = f"transcript:{canonical_url}:{lang}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    info = await asyncio.to_thread(
        _sync_extract_subtitles, canonical_url, platform, lang
    )
    raw_data, actual_lang, is_auto = _find_best_subtitle(info, lang)
    segments = parse_subtitles(raw_data)
    full_text = segments_to_text(segments)

    result = TranscriptResult(
        video_id=video_id,
        language=actual_lang,
        is_auto_generated=is_auto,
        segments=tuple(
            TranscriptSegment(start=s["start"], end=s["end"], text=s["text"])
            for s in segments
        ),
        full_text=full_text,
    )
    _cache.set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Audio stream URL extraction
# ---------------------------------------------------------------------------

_EXT_PREFERENCE = ("m4a", "opus", "mp3", "ogg")


def _select_best_audio(formats: list[dict], quality: str) -> dict:
    """Select the best audio-only format based on quality preference.

    Args:
        formats: List of yt-dlp format dicts.
        quality: "best" for highest bitrate, "smallest" for lowest filesize.

    Returns:
        The selected format dict.

    Raises:
        ExtractionError: If no audio-only formats are available.
    """
    audio_fmts = [
        f for f in formats
        if _has_audio(f) and not _has_video(f) and f.get("url")
    ]
    if not audio_fmts:
        raise ExtractionError("No audio-only formats available for this video")

    if quality == "smallest":
        audio_fmts.sort(key=lambda f: f.get("filesize") or f.get("tbr") or float("inf"))
        return audio_fmts[0]

    # "best": sort by abr descending, prefer m4a/opus/mp3/ogg
    def _sort_key(f: dict) -> tuple:
        abr = f.get("abr") or f.get("tbr") or 0
        ext = f.get("ext", "")
        ext_rank = _EXT_PREFERENCE.index(ext) if ext in _EXT_PREFERENCE else len(_EXT_PREFERENCE)
        return (-abr, ext_rank)

    audio_fmts.sort(key=_sort_key)
    return audio_fmts[0]


# ---------------------------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------------------------

import os
import tempfile


def _sync_transcribe(url: str, platform: Platform, model_name: str) -> dict:
    """Download audio and transcribe with Whisper (runs in thread pool)."""
    import yt_dlp
    import whisper

    tmp = tempfile.NamedTemporaryFile(suffix=".m4a", delete=False)
    tmp_path = tmp.name
    tmp.close()

    config_key = _PLATFORM_CONFIG_KEY.get(platform)
    opts = {
        **load_config(config_key),
        "format": "bestaudio/best",
        "outtmpl": tmp_path,
        "skip_download": False,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise TranscriptionError(f"No info returned for {url}")

        model = whisper.load_model(model_name)
        result = model.transcribe(tmp_path, task="transcribe")

        return {
            "video_id": info.get("id", ""),
            "title": info.get("title", ""),
            "language": result.get("language", ""),
            "text": result.get("text", ""),
            "model": model_name,
        }
    except yt_dlp.utils.DownloadError as exc:
        _map_error(str(exc))
    except Exception as exc:
        raise TranscriptionError(str(exc)) from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def transcribe_audio(url: str) -> TranscriptionResult:
    """Async entry point: download audio and transcribe with Whisper."""
    model_name = os.environ.get("STREAMLENS_WHISPER_MODEL", "base")

    validation = validate_url(url)
    canonical_url = validation.canonical_url
    platform = validation.platform

    cache_key = f"transcription:{canonical_url}:{model_name}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = await asyncio.to_thread(_sync_transcribe, canonical_url, platform, model_name)
    result = TranscriptionResult(
        video_id=data["video_id"],
        title=data["title"],
        language=data["language"],
        text=data["text"],
        model=data["model"],
    )
    _cache.set(cache_key, result)
    return result


async def extract_audio_url(url: str, quality: str = "best") -> AudioStreamInfo:
    """Async entry point: extract the best audio stream URL.

    Args:
        url: Video URL.
        quality: "best" for highest bitrate, "smallest" for lowest filesize.

    Returns:
        AudioStreamInfo with direct stream URL.
    """
    if quality not in ("best", "smallest"):
        raise ExtractionError("quality must be 'best' or 'smallest'")

    validation = validate_url(url)
    canonical_url = validation.canonical_url
    platform = validation.platform
    video_id = validation.video_id or ""

    cache_key = f"audio:{canonical_url}:{quality}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    info = await asyncio.to_thread(_sync_extract, canonical_url, platform)
    formats = info.get("formats") or []
    best = _select_best_audio(formats, quality)

    result = AudioStreamInfo(
        video_id=video_id,
        title=info.get("title", ""),
        url=best["url"],
        format_id=best.get("format_id", ""),
        ext=best.get("ext", ""),
        acodec=best.get("acodec"),
        abr=best.get("abr"),
        filesize=best.get("filesize"),
    )
    _cache.set(cache_key, result)
    return result
