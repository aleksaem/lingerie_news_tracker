"""
Application configuration via pydantic-settings.

Reads values from environment variables or .env file.
Import `settings` singleton throughout the app — do not instantiate Settings directly.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # LLM
    LLM_API_KEY: str
    LLM_MODEL: str = "claude-haiku-4-5"

    # Pipeline settings
    MAX_ARTICLES_PER_DIGEST: int = 5
    MAX_RAW_ARTICLES: int = 100  # скільки статей збираємо до фільтрації

    # News search
    QUERIES_FILE: str = "queries.json"
    NEWS_API_KEY: str = ""  # якщо використовуємо NewsAPI, інакше порожній рядок

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton — імпортується звідусіль
settings = Settings()
