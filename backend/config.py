"""
DataSip Configuration
Loads all settings from the .env file using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini AI
    gemini_api_key: str
    model_name: str = "gemini-3.8-flash"

    # JWT Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    db_url: str = "sqlite:///./datasip.db"

    # App
    app_name: str = "DataSip"
    debug: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "protected_namespaces": ("settings_",),
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance – loaded once at startup."""
    return Settings()
