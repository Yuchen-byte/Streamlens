"""Bilibili video content extractor."""

import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}

VIDEO_INFO_API = "https://api.bilibili.com/x/web-interface/view"
PLAYER_API = "https://api.bilibili.com/x/player/v2"
DANMAKU_API = "https://api.bilibili.com/x/v1/dm/list.so"


def _load_sessdata() -> str | None:
    """Load SESSDATA from environment variable or .env file."""
    sessdata = os.environ.get("BILIBILI_SESSDATA")
    if sessdata:
        return sessdata
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BILIBILI_SESSDATA="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return None


def extract_bvid(url: str) -> str:
    """Extract BV ID from a Bilibili URL."""
    match = re.search(r"(BV[\w]+)", url)
    if not match:
        raise ValueError(f"Cannot extract BV ID from URL: {url}")
    return match.group(1)


async def get_video_info(client: httpx.AsyncClient, bvid: str) -> dict:
    """Fetch video metadata (title, description, tags, stats)."""
    resp = await client.get(VIDEO_INFO_API, params={"bvid": bvid}, headers=HEADERS)
    data = resp.json()
    if data["code"] != 0:
        raise RuntimeError(f"Failed to get video info: {data.get('message')}")
    v = data["data"]
    return {
        "title": v["title"],
        "description": v["desc"],
        "duration": v["duration"],
        "owner": v["owner"]["name"],
        "tags": [],  # filled separately if needed
        "cid": v["cid"],
        "stats": {
            "view": v["stat"]["view"],
            "like": v["stat"]["like"],
            "danmaku": v["stat"]["danmaku"],
            "reply": v["stat"]["reply"],
        },
    }


def _get_cookies_args() -> list[str]:
    """Build yt-dlp cookie arguments if available."""
    cookies_file = os.environ.get("BILIBILI_COOKIES_FILE")
    if not cookies_file:
        cookies_file = str(Path(__file__).resolve().parents[3] / "cookies.txt")
    if Path(cookies_file).exists():
        return ["--cookies", cookies_file]
    # Try SESSDATA -> generate a Netscape cookies file on the fly
    sessdata = _load_sessdata()
    if sessdata:
        tmp_cookie = Path(tempfile.gettempdir()) / "bilibili_cookies.txt"
        tmp_cookie.write_text(
            "# Netscape HTTP Cookie File\n"
            f".bilibili.com\tTRUE\t/\tFALSE\t0\tSESSDATA\t{sessdata}\n",
            encoding="utf-8",
        )
        return ["--cookies", str(tmp_cookie)]
    return []


def _parse_srt(text: str) -> list[str]:
    """Parse SRT subtitle text into a list of lines."""
    lines = []
    for block in re.split(r"\n\n+", text.strip()):
        parts = block.split("\n", 2)
        if len(parts) >= 3:
            content = parts[2].replace("\n", " ").strip()
            if content:
                lines.append(content)
    return lines


def _get_subtitles_ytdlp(url: str) -> list[str]:
    """Use yt-dlp to extract subtitles (auto-generated or CC)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_tpl = str(Path(tmpdir) / "sub")
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-sub", "--write-auto-sub",
            "--sub-lang", "zh-Hans,zh-CN,zh,ai-zh",
            "--convert-subs", "srt",
            "-o", out_tpl,
            *_get_cookies_args(),
            url,
        ]
        subprocess.run(cmd, capture_output=True, timeout=120)
        sub_files = list(Path(tmpdir).glob("*.srt"))
        if not sub_files:
            return []
        text = sub_files[0].read_text(encoding="utf-8")
        return _parse_srt(text)


def _get_subtitles_whisper(url: str) -> list[str]:
    """Download audio via yt-dlp, then transcribe with whisper."""
    print("[info] 未找到字幕，正在使用 whisper 生成...", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = str(Path(tmpdir) / "audio.m4a")
        dl_cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "-o", audio_path,
            *_get_cookies_args(),
            url,
        ]
        subprocess.run(dl_cmd, capture_output=True, timeout=300)
        if not Path(audio_path).exists():
            return []
        import torch
        import whisper
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("base", device=device)
        result = model.transcribe(audio_path, language="zh")
        segments = result.get("segments", [])
        return [seg["text"].strip() for seg in segments if seg.get("text", "").strip()]


async def get_subtitles(url: str) -> list[str]:
    """Extract subtitles: try yt-dlp first, fall back to whisper."""
    lines = _get_subtitles_ytdlp(url)
    if lines:
        return lines
    return _get_subtitles_whisper(url)


async def get_danmaku(client: httpx.AsyncClient, cid: int, limit: int = 200) -> list[str]:
    """Fetch danmaku comments (XML format)."""
    resp = await client.get(DANMAKU_API, params={"oid": cid}, headers=HEADERS)
    resp.encoding = "utf-8"
    try:
        root = ET.fromstring(resp.text)
        items = [d.text for d in root.findall(".//d") if d.text]
        return items[:limit]
    except ET.ParseError:
        return []


async def extract(url: str) -> dict:
    """Full extraction pipeline: video info + subtitles + danmaku."""
    bvid = extract_bvid(url)
    async with httpx.AsyncClient(timeout=30) as client:
        info = await get_video_info(client, bvid)
        cid = info["cid"]
        danmaku = await get_danmaku(client, cid)
    subtitles = await get_subtitles(url)
    return {
        **info,
        "bvid": bvid,
        "subtitles": subtitles,
        "danmaku": danmaku,
    }
