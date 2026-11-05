from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    copilot_github_token: str | None = None
    database_url: str | None = None
    oidc_issuer: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
