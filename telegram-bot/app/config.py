from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Optional: standalone echo-bot only. Per-user Telegram connections
    # live in the main backend (BYOK from profile page), so this
    # service must boot healthy even with no token configured.
    telegram_bot_token: Optional[str] = None
    webhook_url: Optional[str] = None
    database_url: Optional[str] = None
    pg_host: str = "postgres.railway.internal"
    pg_port: int = 5432
    pg_database: str = "railway"
    pg_user: str = "postgres"
    pg_password: str = ""
    port: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
