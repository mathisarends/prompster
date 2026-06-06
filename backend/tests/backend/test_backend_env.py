import logging

import pytest
from pydantic import ValidationError

from backend.env import EnvSettings


class TestEnvSettings:
    def test_dev_uses_debug_log_level_by_default(self) -> None:
        settings = EnvSettings(env="dev", log_level=None, _env_file=None)

        assert settings.effective_log_level == logging.DEBUG

    def test_prod_uses_info_log_level_by_default(self) -> None:
        settings = EnvSettings(env="prod", log_level=None, _env_file=None)

        assert settings.effective_log_level == logging.INFO

    def test_log_level_can_be_overridden_from_environment(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL", "warning")

        settings = EnvSettings(_env_file=None)

        assert settings.effective_log_level == logging.WARNING

    def test_invalid_log_level_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EnvSettings(log_level="verbose", _env_file=None)
