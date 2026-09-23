"""Centralized settings, loaded from environment variables (see .env.example).

Nothing in this service reads os.environ directly outside this module —
that keeps every config value discoverable in one place and testable.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # -- Database --------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://sentinelgrid:change-me-in-production@postgres:5432/sentinelgrid"
    )

    # -- Redis (token blacklist, rate limiting, Phase 4+ event bus) --------
    redis_url: str = "redis://redis:6379/0"
    redis_stream_plate_events: str = "plate_events"
    redis_stream_watchlist_matches: str = "watchlist_matches"

    # -- JWT ---------------------------------------------------------------
    jwt_secret_key: str = "change-me-super-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # -- Camera catalogue (for the /cameras/sync endpoint) -----------------
    ingest_api_url: str = "http://catalogue:9000/api/ingest"
    ingest_api_auth_header: str = ""
    ingest_api_auth_token: str = ""

    # -- CORS ----------------------------------------------------------------
    cors_origins: str = "http://localhost:3000"

    # -- Misc ------------------------------------------------------------------
    # No separate metrics port: /metrics is served on the same port as the
    # API itself (see main.py + metrics.py) — unlike stream_manager and
    # inference, which are plain scripts with no HTTP server of their own
    # otherwise, this service already has one.
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
