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

    # xAI (Grok) Settings
    xai_api_key: str | None = None
    xai_base_url: str = "https://api.x.ai/v1"
    xai_model: str = "grok-2-latest"

    # Groq Settings
    groq_api_key: str | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"

    # GitHub Webhook Settings
    # No fallback secret allowed; must be explicitly configured
    github_webhook_secret: str | None = None
    github_require_signature: bool = True

    # CORS Settings
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Authentication Settings (HS256 JWT, Argon2)
    # auth_secret_key has NO default; fails fast when used if not provided outside tests
    auth_secret_key: str | None = None
    access_token_expire_minutes: int = 60
    auth_algorithm: str = "HS256"

    def get_auth_secret_key(self) -> str:
        """Retrieve auth secret key or fail fast with a clear error."""
        if not self.auth_secret_key:
            raise RuntimeError(
                "AUTH_SECRET_KEY is not set. A secure secret key must be "
                "configured in environment or .env."
            )
        return self.auth_secret_key


settings = Settings()
