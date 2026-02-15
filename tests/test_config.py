"""Unit tests for src/config/settings.py."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.settings import Settings, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_default_values(self):
        """Settings should have sensible defaults for optional fields."""
        with patch.dict(os.environ, {}, clear=True):
            s = Settings(
                _env_file=None,  # disable .env loading for test isolation
            )
        assert s.KAFKA_BROKER == "localhost:9092"
        assert s.SEVERITY_CRITICAL_THRESHOLD == 0.7
        assert s.SEVERITY_WARNING_THRESHOLD == 0.5
        assert s.SEVERITY_INFO_THRESHOLD == 0.3
        assert s.MODEL_PATH == Path("models/")
        assert s.UPLOAD_DIR == Path("data/uploads/")
        assert s.CHROMA_DB_PATH == Path("data/chroma_db/")
        assert s.KNOWLEDGE_BASE_DIR == Path("knowledge_base/")
        assert s.LOG_LEVEL == "INFO"
        assert s.DEBUG is False
        assert s.API_PORT == 8000

    def test_env_var_override(self):
        """Environment variables should override defaults."""
        overrides = {
            "KAFKA_BROKER": "kafka.prod:29092",
            "SEVERITY_CRITICAL_THRESHOLD": "0.8",
            "LOG_LEVEL": "DEBUG",
            "API_PORT": "9000",
            "DEBUG": "true",
        }
        with patch.dict(os.environ, overrides, clear=False):
            s = Settings(_env_file=None)

        assert s.KAFKA_BROKER == "kafka.prod:29092"
        assert s.SEVERITY_CRITICAL_THRESHOLD == 0.8
        assert s.LOG_LEVEL == "DEBUG"
        assert s.API_PORT == 9000
        assert s.DEBUG is True

    def test_database_url_defaults(self):
        """DATABASE_URL should default to local postgres."""
        s = Settings(_env_file=None)
        assert "postgresql" in s.DATABASE_URL
        assert "postgresql" in s.DATABASE_URL_SYNC

    def test_database_url_override(self):
        """DATABASE_URL should be overridable via env."""
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql+asyncpg://user:pass@db:5432/mydb"},
            clear=False,
        ):
            s = Settings(_env_file=None)
        assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@db:5432/mydb"

    def test_model_path_is_path_object(self):
        """MODEL_PATH should be a Path object."""
        s = Settings(_env_file=None)
        assert isinstance(s.MODEL_PATH, Path)

    def test_fulfillment_gap_threshold_defaults_to_warning(self):
        """FULFILLMENT_GAP_THRESHOLD defaults to SEVERITY_WARNING_THRESHOLD."""
        s = Settings(_env_file=None)
        assert s.FULFILLMENT_GAP_THRESHOLD == s.SEVERITY_WARNING_THRESHOLD

    def test_fulfillment_gap_threshold_explicit(self):
        """FULFILLMENT_GAP_THRESHOLD can be set explicitly."""
        with patch.dict(
            os.environ, {"FULFILLMENT_GAP_THRESHOLD": "0.6"}, clear=False
        ):
            s = Settings(_env_file=None)
        assert s.FULFILLMENT_GAP_THRESHOLD == 0.6

    def test_extra_env_vars_ignored(self):
        """Unknown env vars should not raise errors (extra='ignore')."""
        with patch.dict(os.environ, {"TOTALLY_UNKNOWN_VAR": "hi"}, clear=False):
            s = Settings(_env_file=None)
        assert not hasattr(s, "TOTALLY_UNKNOWN_VAR")

    def test_openai_api_key_default_empty(self):
        """OPENAI_API_KEY defaults to empty string when not set."""
        with patch.dict(os.environ, {}, clear=True):
            s = Settings(_env_file=None)
        assert s.OPENAI_API_KEY == ""


class TestGetSettings:
    """Tests for the get_settings singleton."""

    def test_returns_settings_instance(self):
        """get_settings() should return a Settings object."""
        get_settings.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_singleton_returns_same_instance(self):
        """Repeated calls should return the same cached instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_creates_new_instance(self):
        """Clearing the cache should allow a fresh instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # New instance (equal values but different object)
        assert s1 is not s2
