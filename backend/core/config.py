"""
core/config.py
==============
Central application settings loaded from environment variables or a .env file.
All other modules import `get_settings()` — never os.environ directly.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "ProcureAI"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Gemini ─────────────────────────────────────────────────────────────
    gemini_api_key: str = "AIzaSyAP4kjSlKXtGLRft7EYxU0m5_0hYi9K2lw"
    gemini_model: str = "gemini-2.5-pro"
    gemini_max_tokens: int = 2000

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated string in env: ALLOWED_ORIGINS="http://localhost:5173,http://localhost:3000"
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton of Settings."""
    return Settings()
