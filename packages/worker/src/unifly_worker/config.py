"""Runtime configuration loaded from environment variables.

Settings are validated at startup so the worker fails fast on misconfiguration
rather than mid-task. ``firefly_token`` and ``mistral_api_key`` are required
when used; non-localhost ``firefly_url`` over plain HTTP is refused so we never
ship Personal Access Tokens in cleartext.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTNAMES = frozenset({"localhost"})


def _is_private_host(host: str) -> bool:
    """Return True when ``host`` will not transit the public internet.

    Private means: a loopback name, a bare hostname (Docker compose service
    names, intranet short names), or an IP address inside the loopback,
    private (RFC1918), or link-local ranges. FQDNs with no resolvable IP
    information are treated as public — be conservative when unsure.
    """
    if host in _LOOPBACK_HOSTNAMES:
        return True
    # Bare hostname with no dots and no colons -> Docker service name or
    # intranet short name. Cannot be a public DNS name.
    if "." not in host and ":" not in host:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Hostname with dots that isn't an IP -> treat as public FQDN.
        return False
    return addr.is_loopback or addr.is_private or addr.is_link_local


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

    # NOTE: Mistral Workflows worker grouping is configured via the SDK-native
    # ``DEPLOYMENT_NAME`` env var, consumed directly by ``mistralai.workflows``.
    # We don't shadow it here — see worker.py for the startup assertion.
    # https://docs.mistral.ai/workflows/getting-started/core_concepts/deployments

    # --- Firefly III ---
    firefly_url: str = Field(default="http://localhost:8080")
    firefly_token: str = Field(default="")

    # --- Mistral API (used by activities) ---
    mistral_api_key: str = Field(default="")
    mistral_model: str = Field(default="mistral-medium-3-5")

    # --- Companion DB ---
    # No default password embedded — set DATABASE_URL in the environment.
    database_url: str = Field(default="postgresql+asyncpg://companion@localhost:5432/companion")

    # --- Observability ---
    log_level: str = Field(default="INFO")

    # --- Validators ---

    @model_validator(mode="after")
    def _enforce_https_for_remote_firefly(self) -> Settings:
        # Only enforce HTTPS for hosts that can be reached over the public
        # internet. Loopback, RFC1918, link-local, and Docker-style bare
        # hostnames stay on a trusted network so plain HTTP cannot leak the
        # token to a third party. See :func:`_is_private_host`.
        parsed = urlparse(self.firefly_url)
        host = parsed.hostname or ""
        if parsed.scheme == "http" and not _is_private_host(host):
            msg = (
                f"firefly_url uses plain HTTP for public host {host!r}; "
                "tokens would travel in cleartext. Use https:// instead."
            )
            raise ValueError(msg)
        return self

    def require_firefly_token(self) -> str:
        """Return ``firefly_token`` or raise if it's empty.

        Called from the activity that constructs the Firefly client so that
        runs without a configured token fail at task start with a clear
        message rather than deep inside an HTTP call.
        """
        if not self.firefly_token:
            msg = "FIREFLY_TOKEN is not set"
            raise RuntimeError(msg)
        return self.firefly_token

    def require_mistral_api_key(self) -> str:
        """Return ``mistral_api_key`` or raise if it's empty."""
        if not self.mistral_api_key:
            msg = "MISTRAL_API_KEY is not set"
            raise RuntimeError(msg)
        return self.mistral_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Cache is a process-lifetime convenience for ``__main__`` and the worker
    bootstrap. Tests should construct ``Settings(...)`` directly and avoid
    this helper to stay isolated.
    """
    return Settings()
