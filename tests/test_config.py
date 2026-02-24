"""Tests for config module."""

from __future__ import annotations

import os
from unittest.mock import patch

from config import load_config


class TestLoadConfig:

    def test_no_env_vars_returns_empty(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert load_config() == {}

    def test_proxy_only(self) -> None:
        env = {"STREAMLENS_PROXY": "http://127.0.0.1:7897"}
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result == {"proxy": "http://127.0.0.1:7897"}

    def test_cookie_source_only(self) -> None:
        env = {"STREAMLENS_COOKIE_SOURCE": "edge"}
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result == {"cookiesfrombrowser": ("edge",)}

    def test_cookie_file_only(self) -> None:
        env = {"STREAMLENS_COOKIE_FILE": "/tmp/cookies.txt"}
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result == {"cookiefile": "/tmp/cookies.txt"}

    def test_cookie_file_takes_priority_over_source(self) -> None:
        env = {
            "STREAMLENS_COOKIE_SOURCE": "chrome",
            "STREAMLENS_COOKIE_FILE": "/tmp/cookies.txt",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result == {"cookiefile": "/tmp/cookies.txt"}
            assert "cookiesfrombrowser" not in result

    def test_all_vars_set(self) -> None:
        env = {
            "STREAMLENS_PROXY": "http://localhost:8080",
            "STREAMLENS_COOKIE_SOURCE": "firefox",
            "STREAMLENS_COOKIE_FILE": "/tmp/cookies.txt",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result["proxy"] == "http://localhost:8080"
            assert result["cookiefile"] == "/tmp/cookies.txt"
            assert "cookiesfrombrowser" not in result

    def test_blank_values_ignored(self) -> None:
        env = {
            "STREAMLENS_PROXY": "  ",
            "STREAMLENS_COOKIE_SOURCE": "",
        }
        with patch.dict(os.environ, env, clear=True):
            assert load_config() == {}
