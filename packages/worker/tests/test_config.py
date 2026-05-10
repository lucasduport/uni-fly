"""Tests for Settings validators and fail-fast accessors."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unifly_worker.config import Settings


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "firefly_url": "http://localhost:8080",
        "firefly_token": "tok",
        "mistral_api_key": "key",
    }
    base.update(overrides)
    return base


def test_loopback_http_is_allowed() -> None:
    s = Settings(**_kwargs(firefly_url="http://localhost:8080"))
    assert s.firefly_url == "http://localhost:8080"


def test_loopback_127_http_is_allowed() -> None:
    Settings(**_kwargs(firefly_url="http://127.0.0.1:9000"))


def test_remote_https_is_allowed() -> None:
    Settings(**_kwargs(firefly_url="https://firefly.example.com"))


def test_remote_http_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cleartext"):
        Settings(**_kwargs(firefly_url="http://firefly.example.com"))


@pytest.mark.parametrize(
    "url",
    [
        # Docker compose service names — bare hostnames, never public.
        "http://firefly:8080",
        "http://companion-db:5432",
        # RFC1918 private ranges.
        "http://10.0.0.5",
        "http://192.168.1.1",
        "http://172.16.0.10",
        # Link-local.
        "http://169.254.10.10",
        # IPv6 loopback + ULA.
        "http://[::1]",
        "http://[fd00::1]",
    ],
)
def test_private_hosts_allow_plain_http(url: str) -> None:
    Settings(**_kwargs(firefly_url=url))


@pytest.mark.parametrize(
    "url",
    [
        # Public IPv4.
        "http://8.8.8.8",
        "http://1.2.3.4",
        # Public FQDN with subdomain.
        "http://api.example.com",
    ],
)
def test_public_hosts_reject_plain_http(url: str) -> None:
    with pytest.raises(ValidationError, match="cleartext"):
        Settings(**_kwargs(firefly_url=url))


def test_require_firefly_token_returns_value() -> None:
    s = Settings(**_kwargs(firefly_token="abc"))
    assert s.require_firefly_token() == "abc"


def test_require_firefly_token_raises_when_empty() -> None:
    s = Settings(**_kwargs(firefly_token=""))
    with pytest.raises(RuntimeError, match="FIREFLY_TOKEN"):
        s.require_firefly_token()


def test_require_mistral_api_key_raises_when_empty() -> None:
    s = Settings(**_kwargs(mistral_api_key=""))
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        s.require_mistral_api_key()
