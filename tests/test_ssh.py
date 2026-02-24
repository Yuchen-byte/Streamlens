"""Tests for ssh module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from ssh import (
    SSHError,
    _build_ytdlp_cli_args,
    ssh_extract,
    ssh_extract_subtitles,
)


# ---------------------------------------------------------------------------
# _build_ytdlp_cli_args
# ---------------------------------------------------------------------------


class TestBuildYtdlpCliArgs:

    def test_basic_url(self) -> None:
        args = _build_ytdlp_cli_args({}, "https://example.com/video")
        assert args[0] == "yt-dlp"
        assert "--dump-json" in args
        assert args[-1] == "https://example.com/video"

    def test_no_dump_json(self) -> None:
        args = _build_ytdlp_cli_args({}, "https://example.com/video", dump_json=False)
        assert "--dump-json" not in args

    def test_proxy(self) -> None:
        args = _build_ytdlp_cli_args({"proxy": "http://127.0.0.1:7897"}, "https://x.com")
        idx = args.index("--proxy")
        assert args[idx + 1] == "http://127.0.0.1:7897"

    def test_cookies_from_browser(self) -> None:
        args = _build_ytdlp_cli_args({"cookiesfrombrowser": ("chrome",)}, "https://x.com")
        idx = args.index("--cookies-from-browser")
        assert args[idx + 1] == "chrome"

    def test_cookie_file(self) -> None:
        args = _build_ytdlp_cli_args({"cookiefile": "/tmp/cookies.txt"}, "https://x.com")
        idx = args.index("--cookies")
        assert args[idx + 1] == "/tmp/cookies.txt"
    def test_subtitle_langs(self) -> None:
        args = _build_ytdlp_cli_args({"subtitleslangs": ["en", "en-orig"]}, "https://x.com")
        idx = args.index("--sub-langs")
        assert args[idx + 1] == "en,en-orig"

    def test_boolean_flags(self) -> None:
        opts = {"noplaylist": True, "quiet": True, "skip_download": True}
        args = _build_ytdlp_cli_args(opts, "https://x.com")
        assert "--no-playlist" in args
        assert "--quiet" in args
        assert "--skip-download" in args

    def test_false_booleans_omitted(self) -> None:
        args = _build_ytdlp_cli_args({"noplaylist": False}, "https://x.com")
        assert "--no-playlist" not in args

    def test_socket_timeout(self) -> None:
        args = _build_ytdlp_cli_args({"socket_timeout": 30}, "https://x.com")
        idx = args.index("--socket-timeout")
        assert args[idx + 1] == "30"


# ---------------------------------------------------------------------------
# ssh_extract
# ---------------------------------------------------------------------------

SAMPLE_JSON = {"id": "abc123", "title": "Test", "formats": []}


class TestSshExtract:

    @patch("ssh._run_ssh")
    def test_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(SAMPLE_JSON), stderr="",
        )
        result = ssh_extract("https://example.com/video", {}, "user@host")
        assert result["id"] == "abc123"
        mock_run.assert_called_once()

    @patch("ssh._run_ssh")
    def test_nonzero_exit_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Connection refused",
        )
        with pytest.raises(SSHError, match="Connection refused"):
            ssh_extract("https://example.com/video", {}, "user@host")

    @patch("ssh._run_ssh")
    def test_empty_output_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        with pytest.raises(SSHError, match="empty output"):
            ssh_extract("https://example.com/video", {}, "user@host")

    @patch("ssh._run_ssh")
    def test_invalid_json_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="not json", stderr="",
        )
        with pytest.raises(SSHError, match="Invalid JSON"):
            ssh_extract("https://example.com/video", {}, "user@host")


# ---------------------------------------------------------------------------
# ssh_extract_subtitles
# ---------------------------------------------------------------------------


class TestSshExtractSubtitles:

    @patch("ssh._run_ssh")
    def test_success_with_subtitles(self, mock_run: MagicMock) -> None:
        info_json = json.dumps({"id": "abc123", "title": "Test"})
        vtt_content = "WEBVTT\n\n00:00.000 --> 00:01.000\nHello world"
        stdout = f"{info_json}\n---SUBTITLE_BOUNDARY---\n{vtt_content}"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr="",
        )
        result = ssh_extract_subtitles("https://example.com", {}, "user@host", "en")
        assert result["id"] == "abc123"
        assert result["subtitles"]["en"][0]["data"] == vtt_content
        assert result["subtitles"]["en"][0]["ext"] == "vtt"

    @patch("ssh._run_ssh")
    def test_success_without_subtitles(self, mock_run: MagicMock) -> None:
        info_json = json.dumps({"id": "abc123", "title": "Test"})
        stdout = f"{info_json}\n---SUBTITLE_BOUNDARY---\n"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=stdout, stderr="",
        )
        result = ssh_extract_subtitles("https://example.com", {}, "user@host", "en")
        assert result["id"] == "abc123"
        assert "subtitles" not in result or "en" not in result.get("subtitles", {})

    @patch("ssh._run_ssh")
    def test_nonzero_exit_raises(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="timeout",
        )
        with pytest.raises(SSHError, match="timeout"):
            ssh_extract_subtitles("https://example.com", {}, "user@host", "en")
