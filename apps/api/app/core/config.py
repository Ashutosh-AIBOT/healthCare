from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    database_url: str = "postgresql+asyncpg://aarogya:aarogya@localhost:5432/aarogya"
    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    otp_dev_mode: bool = True
    otp_dev_code: str = "123456"
    otp_max_attempts: int = 5
    otp_max_sends_per_hour: int = 3

    auth_login_rate_limit: int = 10
    login_max_failures: int = 10
    login_lockout_minutes: int = 15

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "Aarogya"
    smtp_from_address: str = "noreply@aarogya.local"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket_reports: str = "aarogya-reports"
    minio_bucket_private: str = "aarogya-private"
    minio_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
