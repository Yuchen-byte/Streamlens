"""Remote yt-dlp execution over SSH.

When STREAMLENS_SSH_HOST (or a per-platform variant) is configured, yt-dlp
runs on the remote machine (e.g. a Mac with browser cookies) and the JSON
result is piped back over SSH.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from typing import Optional


class SSHError(Exception):
    """Any failure during remote yt-dlp execution."""


# ---------------------------------------------------------------------------
# CLI arg builder
# ---------------------------------------------------------------------------

_OPT_MAP: dict[str, str] = {
    "proxy": "--proxy",
    "cookiefile": "--cookies",
    "socket_timeout": "--socket-timeout",
}

_BOOL_FLAGS: dict[str, str] = {
    "noplaylist": "--no-playlist",
    "skip_download": "--skip-download",
    "quiet": "--quiet",
    "no_warnings": "--no-warnings",
    "writesubtitles": "--write-subs",
    "writeautomaticsub": "--write-auto-subs",
}


def _build_ytdlp_cli_args(
    opts: dict, url: str, *, dump_json: bool = True,
) -> list[str]:
    """Convert a Python yt-dlp options dict to CLI arguments.

    Pure function — no side effects.
    """
    args: list[str] = ["yt-dlp"]
    if dump_json:
        args.append("--dump-json")

    for key, flag in _BOOL_FLAGS.items():
        if opts.get(key):
            args.append(flag)

    for key, flag in _OPT_MAP.items():
        val = opts.get(key)
        if val is not None:
            args.extend([flag, str(val)])
    # cookiesfrombrowser is a tuple like ("chrome",)
    browser = opts.get("cookiesfrombrowser")
    if browser:
        name = browser[0] if isinstance(browser, tuple) else browser
        args.extend(["--cookies-from-browser", str(name)])

    langs = opts.get("subtitleslangs")
    if langs:
        args.extend(["--sub-langs", ",".join(langs)])

    args.append(url)
    return args


# ---------------------------------------------------------------------------
# SSH runner
# ---------------------------------------------------------------------------


def _run_ssh(
    ssh_host: str, remote_cmd: str, *, timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Execute *remote_cmd* on *ssh_host* via SSH.

    Uses BatchMode to avoid interactive prompts and a 10-second connect timeout.
    """
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        ssh_host,
        remote_cmd,
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ssh_extract(url: str, opts: dict, ssh_host: str) -> dict:
    """Run yt-dlp --dump-json on the remote host and return the parsed dict."""
    args = _build_ytdlp_cli_args(opts, url, dump_json=True)
    remote_cmd = " ".join(shlex.quote(a) for a in args)

    proc = _run_ssh(ssh_host, remote_cmd)
    if proc.returncode != 0:
        raise SSHError(proc.stderr.strip() or f"ssh exited with code {proc.returncode}")
    stdout = proc.stdout.strip()
    if not stdout:
        raise SSHError("Remote yt-dlp returned empty output")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SSHError(f"Invalid JSON from remote yt-dlp: {exc}") from exc


def ssh_extract_subtitles(
    url: str, opts: dict, ssh_host: str, lang: str,
) -> dict:
    """Run yt-dlp on the remote host to extract subtitle data.

    Performs two SSH calls:
    1. yt-dlp --dump-json --write-subs --write-auto-subs --skip-download
       into a remote temp dir
    2. cat the subtitle file from that temp dir

    Returns the info dict with subtitle data injected.
    """
    # Build a remote script that writes subs to a temp dir, then cats them
    sub_opts = {**opts, "writesubtitles": True, "writeautomaticsub": True,
                "skip_download": True, "subtitleslangs": [lang, f"{lang}-orig"]}
    args = _build_ytdlp_cli_args(sub_opts, url, dump_json=True)

    # Remote one-liner: run yt-dlp in a temp dir, dump JSON, then cat any .vtt
    remote_script = (
        "set -e; "
        "TMPDIR=$(mktemp -d); "
        "cd \"$TMPDIR\"; "
        f"{' '.join(shlex.quote(a) for a in args)} > info.json; "
        "cat info.json; "
        "echo '---SUBTITLE_BOUNDARY---'; "
        f"cat \"$TMPDIR\"/*.vtt 2>/dev/null || true; "
        "rm -rf \"$TMPDIR\""
    )

    proc = _run_ssh(ssh_host, remote_script, timeout=90)
    if proc.returncode != 0:
        raise SSHError(proc.stderr.strip() or f"ssh exited with code {proc.returncode}")

    stdout = proc.stdout.strip()
    if not stdout:
        raise SSHError("Remote yt-dlp returned empty output")

    parts = stdout.split("---SUBTITLE_BOUNDARY---", 1)
    json_part = parts[0].strip()
    sub_part = parts[1].strip() if len(parts) > 1 else ""

    try:
        info = json.loads(json_part)
    except json.JSONDecodeError as exc:
        raise SSHError(f"Invalid JSON from remote yt-dlp: {exc}") from exc

    # Inject raw subtitle data so _find_best_subtitle() can find it
    if sub_part:
        subs = info.setdefault("subtitles", {})
        subs.setdefault(lang, []).append({"data": sub_part, "ext": "vtt"})

    return info
