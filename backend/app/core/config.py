"""Pydantic Settings (.env loader)"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "secret"

    # JWT (Auth) — wajib diganti di .env untuk deploy
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # LLM (Goal Decomposition) — provider apa pun yang kompatibel dengan OpenAI API.
    # Default: Google Gemini. Ganti provider cukup lewat .env, tanpa ubah kode.
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL: str = "gemini-3.5-flash-lite"

    # extra="ignore": variabel lama di .env (mis. OPENAI_API_KEY) tidak bikin crash
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
