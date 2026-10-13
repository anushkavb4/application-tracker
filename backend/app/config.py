from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Application Tracker API"
    app_env: str = "development"
    log_level: str = "INFO"
    api_port: int = 8000
    api_key: str = ""
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "application_tracker"
    postgres_user: str = "tracker"
    postgres_password: str = "tracker"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
