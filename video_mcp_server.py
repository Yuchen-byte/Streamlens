"""StreamLens MCP Server — video metadata extraction for YouTube, TikTok, and Douyin."""

from __future__ import annotations

import dataclasses
import json

from mcp.server.fastmcp import FastMCP

from extractor import (
    ExtractionError,
    GeoRestrictionError,
    VideoUnavailableError,
    ensure_ytdlp_installed,
    extract_video_info,
    extract_transcript,
    extract_audio_url,
)
from health import check_health
from search import SearchError, search_videos as _search_videos
from batch import BatchError, extract_playlist_info as _extract_playlist, batch_get_info as _batch_get_info
from validators import InvalidURLError

ensure_ytdlp_installed()

_health = check_health()

mcp = FastMCP("streamlens")


@mcp.tool()
async def get_video_info(url: str) -> str:
    """Extract video metadata including best quality, smallest, and audio-only formats.

    Supports YouTube, TikTok, and Douyin (抖音) URLs.

    Args:
        url: A valid video URL. Supported formats:
             - YouTube: youtube.com/watch, youtu.be, /shorts/, /embed/
             - TikTok: tiktok.com/@user/video/ID, vm.tiktok.com/CODE
             - Douyin: douyin.com/video/ID, v.douyin.com/CODE

    Returns:
        JSON string with video metadata or error details.
    """
    try:
        info = await extract_video_info(url)
        result = info.to_dict()
        if not _health.ffmpeg_available:
            result["_warning"] = _health.ffmpeg_message
        return json.dumps(result, ensure_ascii=False, indent=2)
    except InvalidURLError as exc:
        return json.dumps({"error": "InvalidURL", "message": str(exc)})
    except GeoRestrictionError as exc:
        return json.dumps({"error": "GeoRestriction", "message": str(exc)})
    except VideoUnavailableError as exc:
        return json.dumps({"error": "VideoUnavailable", "message": str(exc)})
    except ExtractionError as exc:
        return json.dumps({"error": "ExtractionError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


@mcp.tool()
async def health_check() -> str:
    """Check StreamLens environment health (yt-dlp, ffmpeg availability).

    Returns:
        JSON string with health status details.
    """
    return json.dumps(dataclasses.asdict(_health), ensure_ascii=False, indent=2)


@mcp.tool()
async def get_transcript(
    url: str, lang: str = "en", format: str = "text"
) -> str:
    """Extract video subtitles/transcript as plain text or timestamped segments.

    Supports YouTube, TikTok, and Douyin (抖音) URLs.
    Uses auto-generated captions when manual subtitles are unavailable.

    Args:
        url: A valid video URL (YouTube, TikTok, or Douyin).
        lang: Preferred subtitle language code (default "en").
              Examples: "en", "zh", "ja", "ko", "es", "fr".
        format: Output format — "text" for plain concatenated text (best for
                summarization), or "segments" for timestamped JSON array
                (best for precise referencing).

    Returns:
        JSON string with transcript data or error details.
    """
    try:
        result = await extract_transcript(url, lang=lang, output_format=format)
        data = result.to_dict()
        if format == "text":
            # For text mode, return compact output
            data = {
                "video_id": data["video_id"],
                "language": data["language"],
                "is_auto_generated": data["is_auto_generated"],
                "full_text": data["full_text"],
            }
        return json.dumps(data, ensure_ascii=False, indent=2)
    except InvalidURLError as exc:
        return json.dumps({"error": "InvalidURL", "message": str(exc)})
    except GeoRestrictionError as exc:
        return json.dumps({"error": "GeoRestriction", "message": str(exc)})
    except VideoUnavailableError as exc:
        return json.dumps({"error": "VideoUnavailable", "message": str(exc)})
    except ExtractionError as exc:
        return json.dumps({"error": "ExtractionError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


@mcp.tool()
async def search_videos(query: str, max_results: int = 5) -> str:
    """Search YouTube videos by keyword.

    Args:
        query: Search query string.
        max_results: Number of results to return (1-20, default 5).

    Returns:
        JSON string with a list of search results or error details.
        Each result includes video_id, title, url, duration, channel, etc.
    """
    try:
        results = await _search_videos(query, max_results=max_results)
        data = [r.to_dict() for r in results]
        return json.dumps(data, ensure_ascii=False, indent=2)
    except SearchError as exc:
        return json.dumps({"error": "SearchError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


@mcp.tool()
async def get_audio_url(url: str, quality: str = "best") -> str:
    """Extract the best audio stream URL from a video (no download).

    Supports YouTube, TikTok, and Douyin (抖音) URLs.
    Returns a direct audio stream URL that can be passed to other tools.

    Args:
        url: A valid video URL (YouTube, TikTok, or Douyin).
        quality: "best" for highest bitrate (default), "smallest" for lowest filesize.

    Returns:
        JSON string with audio stream URL and metadata, or error details.
    """
    try:
        result = await extract_audio_url(url, quality=quality)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    except InvalidURLError as exc:
        return json.dumps({"error": "InvalidURL", "message": str(exc)})
    except GeoRestrictionError as exc:
        return json.dumps({"error": "GeoRestriction", "message": str(exc)})
    except VideoUnavailableError as exc:
        return json.dumps({"error": "VideoUnavailable", "message": str(exc)})
    except ExtractionError as exc:
        return json.dumps({"error": "ExtractionError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


@mcp.tool()
async def get_playlist_info(url: str, max_videos: int = 20) -> str:
    """Extract playlist metadata and video list.

    Args:
        url: A YouTube playlist URL.
        max_videos: Maximum number of videos to include (1-50, default 20).

    Returns:
        JSON string with playlist title, channel, video count, and video list.
    """
    try:
        result = await _extract_playlist(url, max_videos=max_videos)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    except BatchError as exc:
        return json.dumps({"error": "BatchError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


@mcp.tool()
async def batch_get_info(urls: list[str]) -> str:
    """Extract video metadata for multiple URLs in parallel (max 10).

    Partial success is supported — failed URLs return error details
    without blocking successful ones.

    Args:
        urls: List of video URLs (max 10). Supports YouTube, TikTok, Douyin.

    Returns:
        JSON string with total/succeeded/failed counts and per-URL results.
    """
    try:
        result = await _batch_get_info(urls)
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    except BatchError as exc:
        return json.dumps({"error": "BatchError", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"error": "UnexpectedError", "message": str(exc)})


if __name__ == "__main__":
    mcp.run()
