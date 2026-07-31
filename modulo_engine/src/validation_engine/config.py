from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    kb_path: str
    db_url: str
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
