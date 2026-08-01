from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    kb_path: str
    db_url: str
    log_level: str = "INFO"
    assurance_mode: Literal["manual", "coordinator"] = "manual"
    coordinator_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
