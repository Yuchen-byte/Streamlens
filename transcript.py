"""SRT/VTT subtitle parser — converts raw subtitle text to structured segments."""

from __future__ import annotations

import re
from typing import Optional


def _parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.mmm or MM:SS.mmm to seconds."""
    parts = ts.strip().replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0.0


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_VTT_TIMESTAMP_TAG_RE = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
_SRT_SEQUENCE_RE = re.compile(r"^\d+\s*$")
_TIMESTAMP_LINE_RE = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3})"
)


def _clean_text(text: str) -> str:
    """Strip HTML tags, VTT timestamp tags, and normalize whitespace."""
    text = _VTT_TIMESTAMP_TAG_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    return text.strip()


def parse_subtitles(raw: str) -> list[dict]:
    """Parse SRT or VTT subtitle text into a list of segments.

    Each segment is a dict with keys: start, end, text.
    Duplicate/overlapping lines with identical text are merged.
    """
    if not raw or not isinstance(raw, str):
        return []

    segments: list[dict] = []
    lines = raw.splitlines()
    i = 0

    # Skip VTT header
    if lines and lines[0].strip().startswith("WEBVTT"):
        i = 1
        while i < len(lines) and lines[i].strip():
            i += 1

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and SRT sequence numbers
        if not line or _SRT_SEQUENCE_RE.match(line):
            i += 1
            continue

        # Look for timestamp line
        ts_match = _TIMESTAMP_LINE_RE.search(line)
        if not ts_match:
            i += 1
            continue

        start = _parse_timestamp(ts_match.group(1))
        end = _parse_timestamp(ts_match.group(2))
        i += 1

        # Collect text lines until empty line or next timestamp
        text_parts: list[str] = []
        while i < len(lines):
            tl = lines[i].strip()
            if not tl or _TIMESTAMP_LINE_RE.search(tl) or _SRT_SEQUENCE_RE.match(tl):
                break
            cleaned = _clean_text(tl)
            if cleaned:
                text_parts.append(cleaned)
            i += 1

        text = " ".join(text_parts)
        if not text:
            continue

        # Merge with previous if same text (common in auto-generated subs)
        if segments and segments[-1]["text"] == text:
            segments[-1]["end"] = end
        else:
            segments.append({"start": start, "end": end, "text": text})

    return segments


def segments_to_text(segments: list[dict], separator: str = " ") -> str:
    """Concatenate segment texts into a single string."""
    return separator.join(seg["text"] for seg in segments if seg.get("text"))
