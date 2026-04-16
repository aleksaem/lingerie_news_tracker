"""
Application configuration via pydantic-settings.

Reads values from environment variables or .env file.
Import `settings` singleton throughout the app — do not instantiate Settings directly.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    LLM_API_KEY: str
    LLM_MODEL: str = "claude-opus-4-6"

    class Config:
        env_file = ".env"


# TODO: instantiate singleton: settings = Settings()
