from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    copilot_github_token: str | None = None
    database_url: str | None = None
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    session_secret_key: str | None = None
    public_base_url: str = "http://localhost:8000"
    session_ttl_seconds: int = Field(default=28800, gt=0)
    cookie_secure: bool = True
    trusted_proxy_ips: str = ""
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    ip_per_minute: int = Field(default=3, gt=0)
    ip_per_day: int = Field(default=20, gt=0)
    user_per_minute: int = Field(default=3, gt=0)
    user_per_day: int = Field(default=20, gt=0)
    global_per_day: int = Field(default=300, gt=0)
    copilot_model: str | None = None
    dev_auth_enabled: bool = False
    trusted_proxy_hops: int = Field(default=0, ge=0)
    model_timeout_seconds: int = Field(default=30, gt=0)
    trial_timeout_seconds: int = Field(default=90, gt=0)

    @field_validator("session_secret_key", mode="before")
    @classmethod
    def validate_session_secret(cls, value: str | None) -> str | None:
        if value == "":
            return None
        if value is not None and len(value) < 32:
            raise ValueError("SESSION_SECRET_KEY는 32자 이상이어야 합니다.")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
