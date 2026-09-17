"""Pydantic Settings (.env loader)"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "secret"
    OPENAI_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
