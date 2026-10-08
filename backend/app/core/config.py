"""Application configuration settings."""

import os

from pydantic import BaseModel


class Settings(BaseModel):
    """Core settings for ProjectOps."""

    app_name: str = "ProjectOps"
    api_v1_prefix: str = "/api/v1"
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./projectops.db")


settings = Settings()
