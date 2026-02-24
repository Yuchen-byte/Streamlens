"""StreamLens MCP Server — YouTube video metadata extraction tool."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from extractor import (
    ExtractionError,
    GeoRestrictionError,
    VideoUnavailableError,
    ensure_ytdlp_installed,
    extract_video_info,
)
from validators import InvalidURLError

ensure_ytdlp_installed()

mcp = FastMCP("streamlens")


@mcp.tool()
async def get_video_info(url: str) -> str:
    """Extract YouTube video metadata including best quality, smallest, and audio-only formats.

    Args:
        url: A valid YouTube video URL (youtube.com/watch, youtu.be, /shorts/, /embed/).

    Returns:
        JSON string with video metadata or error details.
    """
    try:
        info = await extract_video_info(url)
        return json.dumps(info.to_dict(), ensure_ascii=False, indent=2)
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


if __name__ == "__main__":
    mcp.run()
