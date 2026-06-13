import pytest

from pagedoctor.config import load_settings
from pagedoctor.domain.errors import ConfigError

REQUIRED = {
    "APP_SECRET_KEY": "SENTINEL_APP_KEY",
    "DATABASE_URL": "postgresql+psycopg://u:pw@localhost:5432/db",
    "ANTHROPIC_API_KEY": "SENTINEL_ANTHROPIC_KEY",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "/tmp/sa.json",
}


def _set_required(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)


def test_loads_with_required_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    settings = load_settings(env_file=None)
    assert settings.anthropic_model == "claude-opus-4-8"
    assert settings.anthropic_effort == "high"
    assert "SENTINEL_APP_KEY" not in repr(settings)
    assert "SENTINEL_ANTHROPIC_KEY" not in repr(settings)


def test_missing_required_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_settings(env_file=None)


def test_blank_token_budget_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.setenv("PAGEDOCTOR_TOKEN_BUDGET", "")
    settings = load_settings(env_file=None)
    assert settings.token_budget is None
