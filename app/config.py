from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_app_id: str = ""
    github_app_private_key_path: Path = Path("./secrets/github-app.pem")
    github_webhook_secret: str = ""

    anthropic_api_key: str = ""
    review_model: str = "claude-haiku-4-5"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/pr_reviewer"

    port: int = 8000
    log_level: str = "info"


settings = Settings()
