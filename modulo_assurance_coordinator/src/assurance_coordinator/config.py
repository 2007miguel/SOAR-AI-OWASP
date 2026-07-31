from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str                       # postgresql+psycopg2://...
    engine_url: str                   # http://engine:8000
    log_level: str = "INFO"
    port: int = 8100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
