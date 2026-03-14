"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Project root .env (when running from backend/, cwd .env may not exist)
_project_root = Path(__file__).resolve().parent.parent.parent
_root_env = _project_root / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "sqlite:///./data_aggregator.db"

    # Redis (Celery broker & backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "data-aggregator-results"

    # External APIs
    OPENWEATHER_API_KEY: str = ""
    NEWSAPI_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost"]

    class Config:
        env_file = (_root_env, ".env")  # Try project root first, then cwd
        env_file_encoding = "utf-8"


settings = Settings()
