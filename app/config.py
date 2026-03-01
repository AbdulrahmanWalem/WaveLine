"""
Application configuration using pydantic-settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://waveline:waveline@localhost:5432/wavelinedb"
    REDIS_URL: str = "redis://localhost:6379"
    RESEND_API_KEY: str = ""
    SECRET_KEY: str = ""
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

