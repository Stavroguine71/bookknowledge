"""
Configuration for the Book Intelligence Agent.
All settings are loaded from environment variables.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Book Intelligence Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database (read at runtime, not at import)
    database_url: str = ""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 8192

    # Rate limiting
    max_books_per_batch: int = 20
    max_concurrent_processing: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
