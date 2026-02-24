"""Tests for config module."""

from __future__ import annotations

import os
from unittest.mock import patch

from config import load_config, load_ssh_config


class TestLoadConfigGlobal:

    def test_no_env_vars_returns_empty(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert load_config() == {}

    def test_proxy_only(self) -> None:
        env = {"STREAMLENS_PROXY": "http://127.0.0.1:7897"}
        with patch.dict(os.environ, env, clear=True):
            assert load_config() == {"proxy": "http://127.0.0.1:7897"}

    def test_cookie_source_only(self) -> None:
        env = {"STREAMLENS_COOKIE_SOURCE": "edge"}
        with patch.dict(os.environ, env, clear=True):
            assert load_config() == {"cookiesfrombrowser": ("edge",)}

    def test_cookie_file_only(self) -> None:
        env = {"STREAMLENS_COOKIE_FILE": "/tmp/cookies.txt"}
        with patch.dict(os.environ, env, clear=True):
            assert load_config() == {"cookiefile": "/tmp/cookies.txt"}

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
        env = {"STREAMLENS_PROXY": "  ", "STREAMLENS_COOKIE_SOURCE": ""}
        with patch.dict(os.environ, env, clear=True):
            assert load_config() == {}


class TestLoadConfigPlatformSpecific:

    def test_platform_proxy_overrides_global(self) -> None:
        env = {
            "STREAMLENS_PROXY": "http://global:8080",
            "STREAMLENS_TIKTOK_PROXY": "http://tiktok:9090",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config("TIKTOK")
            assert result["proxy"] == "http://tiktok:9090"

    def test_platform_falls_back_to_global(self) -> None:
        env = {"STREAMLENS_PROXY": "http://global:8080"}
        with patch.dict(os.environ, env, clear=True):
            result = load_config("TIKTOK")
            assert result["proxy"] == "http://global:8080"

    def test_platform_cookie_file_overrides_global(self) -> None:
        env = {
            "STREAMLENS_COOKIE_FILE": "/tmp/global.txt",
            "STREAMLENS_DOUYIN_COOKIE_FILE": "/tmp/douyin.txt",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config("DOUYIN")
            assert result["cookiefile"] == "/tmp/douyin.txt"

    def test_platform_cookie_source_overrides_global(self) -> None:
        env = {
            "STREAMLENS_COOKIE_SOURCE": "chrome",
            "STREAMLENS_TIKTOK_COOKIE_SOURCE": "firefox",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config("TIKTOK")
            assert result["cookiesfrombrowser"] == ("firefox",)

    def test_no_platform_key_ignores_platform_vars(self) -> None:
        env = {
            "STREAMLENS_PROXY": "http://global:8080",
            "STREAMLENS_TIKTOK_PROXY": "http://tiktok:9090",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config()
            assert result["proxy"] == "http://global:8080"

    def test_platform_empty_falls_back_to_global(self) -> None:
        env = {
            "STREAMLENS_PROXY": "http://global:8080",
            "STREAMLENS_DOUYIN_PROXY": "  ",
        }
        with patch.dict(os.environ, env, clear=True):
            result = load_config("DOUYIN")
            assert result["proxy"] == "http://global:8080"


class TestLoadSshConfig:

    def test_no_env_returns_none(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert load_ssh_config() is None

    def test_global_ssh_host(self) -> None:
        env = {"STREAMLENS_SSH_HOST": "user@macbook.local"}
        with patch.dict(os.environ, env, clear=True):
            assert load_ssh_config() == "user@macbook.local"

    def test_platform_override(self) -> None:
        env = {
            "STREAMLENS_SSH_HOST": "user@global.local",
            "STREAMLENS_DOUYIN_SSH_HOST": "user@douyin.local",
        }
        with patch.dict(os.environ, env, clear=True):
            assert load_ssh_config("DOUYIN") == "user@douyin.local"

    def test_platform_falls_back_to_global(self) -> None:
        env = {"STREAMLENS_SSH_HOST": "user@macbook.local"}
        with patch.dict(os.environ, env, clear=True):
            assert load_ssh_config("TIKTOK") == "user@macbook.local"

    def test_blank_returns_none(self) -> None:
        env = {"STREAMLENS_SSH_HOST": "  "}
        with patch.dict(os.environ, env, clear=True):
            assert load_ssh_config() is None
