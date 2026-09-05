"""All configuration comes from environment variables. No secrets in code."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://medlens:medlens@localhost:5432/medlens"

    # Backend only. Never sent to the browser.
    anthropic_api_key: str = ""

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"

    storage_dir: str = "./storage"
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
