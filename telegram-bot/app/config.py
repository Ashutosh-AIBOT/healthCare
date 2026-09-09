from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    telegram_bot_token: str
    webhook_url: Optional[str] = None
    database_url: str
    pg_host: str = "postgres.railway.internal"
    pg_port: int = 5432
    pg_database: str = "railway"
    pg_user: str = "postgres"
    pg_password: str
    port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
