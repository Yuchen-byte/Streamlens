"""Environment health checks for yt-dlp and ffmpeg availability."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HealthStatus:
    ytdlp_available: bool
    ytdlp_version: Optional[str]
    ffmpeg_available: bool
    ffmpeg_path: Optional[str]
    ffmpeg_message: str
    whisper_available: bool
    whisper_model: str


def check_health() -> HealthStatus:
    """Check environment health. Never raises."""
    # yt-dlp
    ytdlp_available = False
    ytdlp_version: Optional[str] = None
    try:
        import yt_dlp
        ytdlp_available = True
        ytdlp_version = getattr(yt_dlp, "version", None)
        if ytdlp_version and hasattr(ytdlp_version, "__version__"):
            ytdlp_version = ytdlp_version.__version__
        elif isinstance(ytdlp_version, str):
            pass
        else:
            ytdlp_version = str(ytdlp_version) if ytdlp_version else None
    except ImportError:
        pass

    # ffmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    ffmpeg_available = ffmpeg_path is not None
    if ffmpeg_available:
        ffmpeg_message = "ffmpeg is available"
    else:
        ffmpeg_message = (
            "ffmpeg not found. Some formats may be unavailable. "
            "Install: conda install -c conda-forge ffmpeg  |  "
            "apt: sudo apt install ffmpeg  |  "
            "brew: brew install ffmpeg"
        )

    # whisper
    whisper_available = False
    whisper_model = os.environ.get("STREAMLENS_WHISPER_MODEL", "base")
    try:
        import whisper  # noqa: F401
        whisper_available = True
    except ImportError:
        pass

    return HealthStatus(
        ytdlp_available=ytdlp_available,
        ytdlp_version=ytdlp_version,
        ffmpeg_available=ffmpeg_available,
        ffmpeg_path=ffmpeg_path,
        ffmpeg_message=ffmpeg_message,
        whisper_available=whisper_available,
        whisper_model=whisper_model,
    )
