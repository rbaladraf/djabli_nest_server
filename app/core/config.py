from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://djabli:djabli_secret@localhost:5432/djablinest"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_MB: int = 10
    CORS_ORIGINS: str = "http://localhost"
    INITIAL_SUPERADMIN_USERNAME: str = "superadmin"
    INITIAL_SUPERADMIN_PASSWORD: str = "ChangeMe123!"
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    APP_ENV: str = "development"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
