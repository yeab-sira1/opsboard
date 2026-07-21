"""Application runtime configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    """Runtime configuration for the application."""

    model_config = ConfigDict(frozen=True)

    app_name: str = "OpsBoard"
    app_version: str = "0.1.0"

    database_url: str = "sqlite+pysqlite:///:memory:"
    database_echo: bool = False

    cache_enabled: bool = True
    default_page_size: int = 25

    log_level: str = "INFO"
    timezone: str = "UTC"


settings = Settings()