from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_DB_URL = f"sqlite+aiosqlite:///{_REPO_ROOT.as_posix()}/projectops.db"


class Settings(BaseSettings):
    """Core settings for ProjectOps."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ProjectOps"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = _DEFAULT_DB_URL

    # LLM Settings
    # Default provider is claude per AGENTS.md; "mock" must be explicitly configured
    llm_provider: str = "claude"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-7-sonnet-20250219"

    # GitHub Webhook Settings
    # No fallback secret allowed; must be explicitly configured
    github_webhook_secret: str | None = None
    github_require_signature: bool = True

    # CORS Settings
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
