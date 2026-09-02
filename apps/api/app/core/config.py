from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    database_url: str = "postgresql+asyncpg://aarogya:aarogya@localhost:5432/aarogya"
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    otp_dev_mode: bool = True
    otp_dev_code: str = "123456"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Aarogya"
    smtp_from_address: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
