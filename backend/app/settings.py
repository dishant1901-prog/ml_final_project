"""Explicit roots; environment values and secrets never enter error messages."""

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
        env_ignore_empty=True,
    )
    data_root: Path
    himaroad_data_dir: Path
    llm_base_url: str | None = None
    llm_model: str | None = None
    report_font: Path | None = None
    local_auth_admin_username: str | None = None
    local_auth_admin_password_hash: SecretStr | None = None
    local_auth_viewer_username: str | None = None
    local_auth_viewer_password_hash: SecretStr | None = None
    local_auth_cookie_secret: SecretStr | None = None
    local_service_token: SecretStr | None = None
    rate_limit_per_minute: int = Field(default=600, ge=60, le=10_000)
    max_queued_jobs: int = Field(default=16, ge=1, le=256)
    job_stale_seconds: int = Field(default=7200, ge=300, le=86_400)

    @field_validator("data_root", "himaroad_data_dir")
    @classmethod
    def absolute_root(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("root must be absolute")
        return value.resolve()

    @field_validator("llm_base_url")
    @classmethod
    def http_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("LLM endpoint must be an HTTP URL")
            if parsed.username or parsed.password:
                raise ValueError("credentials must not appear in endpoint URL")
        return value

    @model_validator(mode="after")
    def separate_roots(self) -> "Settings":
        reference = (self.data_root / "reference").resolve()
        if self.himaroad_data_dir.is_relative_to(reference):
            raise ValueError("HimaRoad root must be outside the reference root")
        if bool(self.llm_base_url) != bool(self.llm_model):
            raise ValueError("LLM endpoint and model must be supplied together")
        admin = bool(self.local_auth_admin_username)
        admin_hash = bool(self.local_auth_admin_password_hash)
        viewer = bool(self.local_auth_viewer_username)
        viewer_hash = bool(self.local_auth_viewer_password_hash)
        if admin != admin_hash or viewer != viewer_hash:
            raise ValueError(
                "Each local user requires both a username and password hash"
            )
        if (admin or viewer) and self.local_auth_cookie_secret is None:
            raise ValueError("Local authentication requires a cookie signing secret")
        names = [
            name
            for name in (
                self.local_auth_admin_username,
                self.local_auth_viewer_username,
            )
            if name
        ]
        if len(names) != len(set(names)):
            raise ValueError("Local authentication usernames must be distinct")
        return self
