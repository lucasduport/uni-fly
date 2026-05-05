"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker settings.

    Values are read from environment variables (or a ``.env`` file at the repo
    root during local development). All fields are immutable after load.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Mistral Workflows runtime ---
    workflow_task_queue: str = Field(default="unifly-worker")

    # --- Firefly III ---
    firefly_url: str = Field(default="http://localhost:8080")
    firefly_token: str = Field(default="")

    # --- Mistral API (used by activities) ---
    mistral_api_key: str = Field(default="")
    mistral_model: str = Field(default="mistral-large-latest")

    # --- Observability ---
    log_level: str = Field(default="INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
