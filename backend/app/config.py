"""
config.py
---------
Centralized application configuration.

All settings are loaded from environment variables at startup.
Secrets (API keys, credentials) are expected to be injected via
Azure Container Apps environment variables, which can reference
Azure Key Vault secrets directly.

Environment Variables Required:
    - ANTHROPIC_API_KEY: API key for Claude (Anthropic). Stored in Azure Key Vault.
    - ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins.

Environment Variables Optional:
    - LOG_LEVEL: Logging verbosity. Defaults to "INFO".
    - ANTHROPIC_MODEL: Claude model identifier. Defaults to "claude-sonnet-4-20250514".
    - OPEN_LIBRARY_BASE_URL: Base URL for Open Library API. Defaults to production.
    - MAX_CANDIDATES: Maximum number of book candidates to return. Defaults to 5.
    - REQUEST_TIMEOUT: HTTP request timeout in seconds. Defaults to 30.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings for validation and type coercion.
    In production, these values are injected by Azure Container Apps
    and secrets are referenced from Azure Key Vault.
    """

    # ----------------------------------------------------------------
    # Secrets (stored in Azure Key Vault, referenced via App Settings)
    # ----------------------------------------------------------------
    anthropic_api_key: str

    # ----------------------------------------------------------------
    # CORS Configuration
    # ----------------------------------------------------------------
    allowed_origins: str = "http://localhost:5173"

    # ----------------------------------------------------------------
    # Claude AI Configuration
    # ----------------------------------------------------------------
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ----------------------------------------------------------------
    # Open Library Configuration
    # ----------------------------------------------------------------
    open_library_base_url: str = "https://openlibrary.org"
    open_library_covers_url: str = "https://covers.openlibrary.org"

    # ----------------------------------------------------------------
    # Application Behavior
    # ----------------------------------------------------------------
    max_candidates: int = 5
    request_timeout: int = 30
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of application settings.

    The lru_cache decorator ensures that environment variables are read
    only once during the application lifecycle, avoiding redundant I/O
    on every request.
    """
    return Settings()
