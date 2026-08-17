from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_app_id: str = ""
    github_app_private_key_path: Path = Path("./secrets/github-app.pem")
    # Contents of the PEM, used in hosted environments instead of a file on disk.
    # Env var wins over the file if both are set.
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    anthropic_api_key: str = ""
    review_model: str = "claude-haiku-4-5"

    database_url: str = "sqlite:///./data/reviews.db"
    # Chroma persistence lives inside the data dir so hosted deploys can use
    # a single mounted volume for both sqlite and vector storage.
    chroma_path: Path = Path("./data/chroma")

    # If set, /dashboard requires a Bearer <this-token>. If empty, /dashboard
    # is unauthenticated (dev only — do not deploy without setting this).
    dashboard_token: str = ""

    port: int = 8000
    log_level: str = "info"


settings = Settings()
