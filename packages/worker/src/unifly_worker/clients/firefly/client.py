"""Async httpx wrapper around the Firefly III v1 REST API.

This module is a thin transport: one method per endpoint, no domain logic, no
opinionated defaults beyond timeout. Higher-level constructs (search DSL
helpers, dedup-by-external-id, retry policies) live in
:mod:`unifly_worker.clients.firefly.queries` or in activity modules.

Logging policy: the ``Authorization`` header is set on the underlying
``httpx.AsyncClient`` at construction time and never logged. ``__repr__`` does
not include it. Request/response details are emitted at DEBUG; lifecycle
events at INFO; transport failures at WARNING/ERROR (the caller decides
whether the failure is recoverable).
"""

from __future__ import annotations

import json
import logging
from types import TracebackType
from typing import Self

import httpx

from unifly_worker.clients.firefly.errors import FireflyAPIError, FireflyValidationError
from unifly_worker.clients.firefly.models import (
    Account,
    Category,
    Page,
    Single,
    Tag,
    TransactionGroupIn,
    TransactionGroupRead,
    TransactionRead,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0


class FireflyClient:
    """Async client for the Firefly III v1 REST API.

    Args:
        base_url: Root URL of the Firefly III instance.
        token: Personal Access Token created in the Firefly III UI.
        timeout: Per-request timeout in seconds.
        transport: Optional pre-built httpx transport (used by tests, or for
            wrapping with retry/instrumentation transports in production).
        client: Optional pre-built ``httpx.AsyncClient``. When supplied,
            ``base_url``, ``timeout``, and ``transport`` are ignored — the
            caller owns lifecycle. Useful for sharing pools or installing
            event hooks.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not token:
            msg = "Firefly III token must not be empty"
            raise ValueError(msg)
        self._owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(
                base_url=base_url.rstrip("/"),
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                transport=transport,
            )
        self._client = client
        logger.info("FireflyClient initialised base_url=%s", base_url)

    def __repr__(self) -> str:
        # Never include the token.
        return f"FireflyClient(base_url={self._client.base_url!s})"

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
            logger.debug("FireflyClient httpx client closed")

    # -- transport ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: object | None = None,
        params: dict[str, str | int | float | bool | None] | None = None,
    ) -> dict[str, object]:
        logger.debug("HTTP %s %s", method, path)
        response = await self._client.request(
            method, path, json=json_body, params=_drop_none(params)
        )
        return _decode(response, method, path)

    # -- transactions ------------------------------------------------------

    async def create_transaction(self, group: TransactionGroupIn) -> TransactionGroupRead:
        payload = group.model_dump(mode="json", exclude_none=True)
        body = await self._request("POST", "/api/v1/transactions", json_body=payload)
        return Single[TransactionGroupRead].model_validate(body).data

    async def get_transaction(self, transaction_id: int) -> TransactionGroupRead:
        body = await self._request("GET", f"/api/v1/transactions/{transaction_id}")
        return Single[TransactionGroupRead].model_validate(body).data

    async def update_transaction(
        self, transaction_id: int, group: TransactionGroupIn
    ) -> TransactionGroupRead:
        payload = group.model_dump(mode="json", exclude_none=True)
        body = await self._request(
            "PUT", f"/api/v1/transactions/{transaction_id}", json_body=payload
        )
        return Single[TransactionGroupRead].model_validate(body).data

    async def search_transaction_groups(
        self, query: str, *, page: int = 1, limit: int = 50
    ) -> Page[TransactionGroupRead]:
        """Search the transactions endpoint, returning raw transaction groups.

        Callers that need a flat list of splits should flatten the result —
        keeping the transport-level method shape-faithful avoids hidden
        coercions and surprises.
        """
        body = await self._request(
            "GET",
            "/api/v1/search/transactions",
            params={"query": query, "page": page, "limit": limit},
        )
        return Page[TransactionGroupRead].model_validate(body)

    # -- categories --------------------------------------------------------

    async def list_categories(self, *, page: int = 1, limit: int = 50) -> Page[Category]:
        body = await self._request(
            "GET", "/api/v1/categories", params={"page": page, "limit": limit}
        )
        return Page[Category].model_validate(body)

    async def create_category(self, name: str) -> Category:
        body = await self._request("POST", "/api/v1/categories", json_body={"name": name})
        return Single[Category].model_validate(body).data

    # -- tags --------------------------------------------------------------

    async def list_tags(self, *, page: int = 1, limit: int = 50) -> Page[Tag]:
        body = await self._request("GET", "/api/v1/tags", params={"page": page, "limit": limit})
        return Page[Tag].model_validate(body)

    async def create_tag(self, tag: str) -> Tag:
        body = await self._request("POST", "/api/v1/tags", json_body={"tag": tag})
        return Single[Tag].model_validate(body).data

    # -- accounts ----------------------------------------------------------

    async def list_accounts(self, *, page: int = 1, limit: int = 50) -> Page[Account]:
        body = await self._request("GET", "/api/v1/accounts", params={"page": page, "limit": limit})
        return Page[Account].model_validate(body)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Re-export to keep the public type surface stable for callers that flatten.
__all__ = ["FireflyClient", "TransactionRead"]


def _drop_none(
    params: dict[str, str | int | float | bool | None] | None,
) -> dict[str, str | int | float | bool] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _decode(response: httpx.Response, method: str, path: str) -> dict[str, object]:
    """Return the JSON body of ``response`` or raise a typed Firefly error."""
    if response.is_success:
        if not response.content:
            return {}
        try:
            decoded = response.json()
        except json.JSONDecodeError as exc:
            logger.error(
                "Firefly returned non-JSON success response method=%s path=%s status=%d",
                method,
                path,
                response.status_code,
            )
            raise FireflyAPIError(
                response.status_code, response.text, "Invalid JSON in response"
            ) from exc
        return decoded if isinstance(decoded, dict) else {"data": decoded}

    body: dict[str, object] | str
    try:
        decoded = response.json()
        body = decoded if isinstance(decoded, dict) else {"raw": decoded}
    except json.JSONDecodeError:
        body = response.text

    if response.status_code == 422 and isinstance(body, dict):
        logger.warning("Firefly validation error method=%s path=%s status=422", method, path)
        raise FireflyValidationError(body)

    log = logger.error if response.status_code >= 500 else logger.warning
    log("Firefly API error method=%s path=%s status=%d", method, path, response.status_code)
    raise FireflyAPIError(response.status_code, body)
