from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    env: str = "local"
    sqlite_path: Path = Path("data/local/fraud_v2.sqlite")
    api_token: str = "dev-token-change-me"


def get_settings() -> Settings:
    return Settings()
