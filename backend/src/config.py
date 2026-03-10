"""Application configuration via environment variables"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/tradingbot"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://yourdomain.com"]
    BOT_PROCESS_NAME: str = "trading_bot"
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"
        extra = "ignore"
