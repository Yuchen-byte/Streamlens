"""Immutable data structures for video metadata."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VideoFormat:
    """Single video/audio format entry."""

    format_id: str
    ext: str
    resolution: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    tbr: Optional[float] = None
    url: Optional[str] = None
    format_note: Optional[str] = None


@dataclass(frozen=True)
class VideoInfo:
    """Aggregated video metadata with selected format variants."""

    video_id: str
    title: str
    webpage_url: str
    uploader: Optional[str] = None
    uploader_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    duration_string: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    best_quality_video: Optional[VideoFormat] = None
    smallest_video: Optional[VideoFormat] = None
    audio_only: Optional[VideoFormat] = None
    subtitles_summary: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to plain dictionary."""
        return dataclasses.asdict(self)
