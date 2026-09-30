from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = (
        "postgresql+psycopg://agentops:agentops@localhost:5432/agentops"
    )
    redis_url: str = "redis://localhost:6379/0"
    auth_secret: str = "dev-only-change-me-agentops-secret-32chars"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    refresh_cookie_name: str = "agentops_refresh"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
