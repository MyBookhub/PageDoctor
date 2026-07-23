from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pagedoctor.domain.errors import ConfigError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: Literal["development", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_secret_key: SecretStr
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: str
    anthropic_api_key: SecretStr
    anthropic_model: str = "claude-opus-4-8"
    anthropic_effort: Literal["low", "medium", "high", "max"] = "high"
    token_budget: int | None = Field(
        default=None,
        validation_alias=AliasChoices("PAGEDOCTOR_TOKEN_BUDGET", "token_budget"),
    )
    google_service_account_file: str
    google_service_account_email: str | None = None
    # Fixed Drive folder for the versioned "_lektoriert_vN" copies (issue #31). The service
    # account has write access there; a more elegant location strategy is a later version.
    lektorat_folder_id: str = "1wEMp95LbYq7zBK0-8QfrrEYI1dKqSy9i"
    # Issue #34: pace the write phase like a human editor — one randomized pause before
    # each comment, copy uploaded only after the configured session length. Deliberately
    # inefficient; off by default. The session lands in [87.5%, 100%] of the minutes value.
    simulate_human_work: bool = False
    simulate_human_work_minutes: int = Field(default=120, ge=1)
    # Optional shared-secret gate for the PM web app. When unset (local dev) auth is off;
    # set both when the app is deployed so it is not openly reachable. SSO is a future swap.
    basic_auth_user: str | None = None
    basic_auth_password: SecretStr | None = None
    # Bearer token gating the add-on findings API. Unset (local dev) leaves it open; set it
    # before the backend is exposed (e.g. behind a tunnel) so the endpoint requires the token.
    addon_token: SecretStr | None = None

    @field_validator("token_budget", mode="before")
    @classmethod
    def _blank_budget_is_none(cls, value: object) -> object:
        if value == "":
            return None
        return value


def load_settings(env_file: str | None = ".env") -> Settings:
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        invalid_fields = ", ".join(
            ".".join(str(part) for part in error["loc"]) for error in exc.errors()
        )
        raise ConfigError(f"invalid configuration: {invalid_fields}") from exc
