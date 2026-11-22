import logging

import pytest
from pydantic import ValidationError

from backend.env import EnvSettings, LoggingLevelSettings


class TestEnvSettings:
    def test_normalizes_frontend_url_and_exposes_allowed_origin(self) -> None:
        settings = EnvSettings(
            env="prod",
            frontend_base_url="https://app.example.com/",
            _env_file=None,
        )

        assert settings.is_dev is False
        assert settings.is_prod is True
        assert settings.frontend_base_url == "https://app.example.com"
        assert settings.allowed_origins == ["https://app.example.com"]

    def test_rejects_frontend_url_without_http_scheme(self) -> None:
        with pytest.raises(ValidationError, match="Frontend URL"):
            EnvSettings(frontend_base_url="app.example.com", _env_file=None)


class TestLoggingLevelSettings:
    def test_dev_uses_debug_log_level_by_default(self) -> None:
        settings = LoggingLevelSettings(env="dev", log_level=None, _env_file=None)

        assert settings.effective_log_level == logging.DEBUG

    def test_prod_uses_info_log_level_by_default(self) -> None:
        settings = LoggingLevelSettings(env="prod", log_level=None, _env_file=None)

        assert settings.effective_log_level == logging.INFO

    def test_log_level_can_be_overridden_from_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL", "warning")

        settings = LoggingLevelSettings(_env_file=None)

        assert settings.effective_log_level == logging.WARNING

    def test_invalid_log_level_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LoggingLevelSettings(log_level="verbose", _env_file=None)

    def test_empty_log_level_uses_environment_default(self) -> None:
        settings = LoggingLevelSettings(env="prod", log_level="   ", _env_file=None)

        assert settings.effective_log_level == logging.INFO
