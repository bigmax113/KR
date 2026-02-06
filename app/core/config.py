from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service
    APP_NAME: str = "ai-recipes-backend"
    ENV: str = "dev"  # dev|staging|prod
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS (comma-separated origins)
    CORS_ORIGINS: str = "*"

    # xAI / Grok
    XAI_BASE_URL: str = "https://api.x.ai"
    XAI_API_KEY: str = Field(default="", repr=False)
    # Tooling model is hardcoded in app/api/routes.py (Render env cannot override it).
    # You can use a different model for translation/adaptation if you want.
    XAI_MODEL_GENERAL: str = "grok-4-1-fast-reasoning"
    XAI_TIMEOUT_S: float = 60.0

    # Responses API behavior
    XAI_STORE_MESSAGES: bool = False  # set false to avoid server-side storage

    # Data paths (file-based MVP storage)
    DATA_DIR: str = "data"
    ROBOT_PROFILES_DIR: str = "data/robot_profiles"
    RECIPES_DIR: str = "data/recipes"

    # Caching (in-memory TTL cache for MVP)
    CACHE_TTL_S: int = 60 * 60 * 24  # 24h
    CACHE_MAXSIZE: int = 10_000

    # Domain controls for web recipe search (comma-separated)
    WEB_ALLOWED_DOMAINS: str = ""     # e.g. "allrecipes.com,bbcgoodfood.com"
    WEB_EXCLUDED_DOMAINS: str = "pinterest.com,facebook.com,instagram.com,tiktok.com"


settings = Settings()
