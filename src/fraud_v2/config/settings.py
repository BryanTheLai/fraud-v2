from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRAUD_", env_file=".env", extra="ignore")

    env: str = "local"
    sqlite_path: Path = Path("data/local/fraud_v2.sqlite")
    store_backend: str = "sqlite"
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2"
    api_token: str = "dev-token-change-me"
    api_tokens: str = ""
    auth_mode: str = "token"
    jwt_secret: str = ""
    jwt_issuer: str = "fraud-v2-local"
    jwt_audience: str = "fraud-v2-api"
    jwt_leeway_seconds: int = 30
    jwt_roles_claim: str = "roles"


def get_settings() -> Settings:
    return Settings()
