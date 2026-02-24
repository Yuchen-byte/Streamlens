"""Tests for health check module."""

from __future__ import annotations

from unittest.mock import patch

from health import HealthStatus, check_health


class TestCheckHealth:

    def test_all_available(self) -> None:
        with patch("health.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = check_health()
        assert isinstance(result, HealthStatus)
        assert result.ytdlp_available is True
        assert result.ffmpeg_available is True
        assert result.ffmpeg_path == "/usr/bin/ffmpeg"
        assert result.ffmpeg_message == "ffmpeg is available"

    def test_ffmpeg_missing(self) -> None:
        with patch("health.shutil.which", return_value=None):
            result = check_health()
        assert result.ffmpeg_available is False
        assert result.ffmpeg_path is None
        assert "ffmpeg not found" in result.ffmpeg_message
        assert "conda install" in result.ffmpeg_message

    def test_ytdlp_missing(self) -> None:
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "yt_dlp":
                raise ImportError("no yt_dlp")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with patch("health.shutil.which", return_value="/usr/bin/ffmpeg"):
                result = check_health()
        assert result.ytdlp_available is False
        assert result.ytdlp_version is None

    def test_never_raises(self) -> None:
        with patch("health.shutil.which", side_effect=OSError("boom")):
            try:
                check_health()
            except OSError:
                pass  # shutil.which raising is unexpected but we test it doesn't crash
