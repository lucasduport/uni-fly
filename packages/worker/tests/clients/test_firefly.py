"""Tests for the Firefly III httpx client.

HTTP is stubbed via ``pytest_httpx`` so the suite runs offline. Coverage focus:
auth header, request/response shape, error mapping, paging structure.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

import httpx
import pytest
from pytest_httpx import HTTPXMock

from unifly_worker.clients.firefly import (
    FireflyAPIError,
    FireflyClient,
    FireflyValidationError,
    TransactionGroupIn,
    TransactionSplitIn,
    find_transaction_by_external_id,
)
from unifly_worker.clients.firefly.queries import _escape_dsl_value

BASE_URL = "http://firefly.test"
TOKEN = "test-token"


@pytest.fixture
async def client() -> AsyncIterator[FireflyClient]:
    """Yield a fully-managed FireflyClient (closed even if a test fails early)."""
    async with FireflyClient(BASE_URL, TOKEN) as fc:
        yield fc


def _split() -> TransactionSplitIn:
    return TransactionSplitIn(
        type="withdrawal",
        date=datetime(2026, 5, 8, 12, 0, 0),
        amount=Decimal("12.34"),
        description="Test purchase",
        source_name="Checking",
        destination_name="Tesco",
        external_id="abc-123",
    )


# ---------------------------------------------------------------------------
# Auth + transport
# ---------------------------------------------------------------------------


def test_init_rejects_empty_token() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        FireflyClient(BASE_URL, "")


def test_repr_does_not_leak_token() -> None:
    fc = FireflyClient(BASE_URL, "supersecret-abc-123")
    assert "supersecret" not in repr(fc)
    assert "Bearer" not in repr(fc)


async def test_bearer_header_set_on_every_request(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/categories?page=1&limit=50",
        json={"data": [], "meta": {"pagination": {}}},
    )
    await client.list_categories()
    request = httpx_mock.get_requests()[0]
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert request.headers["accept"] == "application/json"


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


async def test_create_transaction_posts_wrapped_body(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/v1/transactions",
        json={
            "data": {
                "id": 42,
                "attributes": {
                    "transactions": [
                        {
                            "transaction_journal_id": 100,
                            "type": "withdrawal",
                            "date": "2026-05-08T12:00:00Z",
                            "description": "Test purchase",
                            "amount": "12.34",
                            "external_id": "abc-123",
                        }
                    ]
                },
            }
        },
    )
    group = TransactionGroupIn(transactions=[_split()], apply_rules=False)
    result = await client.create_transaction(group)

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.read())
    assert "transactions" in payload
    assert payload["apply_rules"] is False
    assert payload["transactions"][0]["description"] == "Test purchase"
    assert payload["transactions"][0]["external_id"] == "abc-123"
    assert result.id == 42
    assert result.attributes.transactions[0].external_id == "abc-123"


async def test_create_transaction_omits_unset_policy_flags(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    """When the caller doesn't set apply_rules/error_if_duplicate_hash, they
    must NOT be sent — the wire model is unopinionated."""
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/v1/transactions",
        json={
            "data": {
                "id": 1,
                "attributes": {
                    "transactions": [
                        {
                            "transaction_journal_id": 1,
                            "type": "withdrawal",
                            "date": "2026-05-08T12:00:00Z",
                            "description": "x",
                            "amount": "1.00",
                        }
                    ]
                },
            }
        },
    )
    group = TransactionGroupIn(transactions=[_split()])  # no flags set
    await client.create_transaction(group)

    payload = json.loads(httpx_mock.get_requests()[0].read())
    assert "apply_rules" not in payload
    assert "error_if_duplicate_hash" not in payload


async def test_422_raises_validation_error(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/v1/transactions",
        status_code=422,
        json={
            "message": "The given data was invalid.",
            "errors": {"transactions.0.description": ["The description field is required."]},
        },
    )
    with pytest.raises(FireflyValidationError) as exc:
        await client.create_transaction(TransactionGroupIn(transactions=[_split()]))
    assert exc.value.status_code == 422
    assert exc.value.errors["transactions.0.description"] == ["The description field is required."]


async def test_5xx_raises_api_error(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/transactions/7",
        status_code=503,
        json={"message": "Service Unavailable"},
    )
    with pytest.raises(FireflyAPIError) as exc:
        await client.get_transaction(7)
    assert exc.value.status_code == 503
    assert "Service Unavailable" in str(exc.value)


async def test_repr_omits_response_body(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/transactions/7",
        status_code=503,
        json={"message": "Service Unavailable", "secret": "should-not-leak"},
    )
    with pytest.raises(FireflyAPIError) as exc:
        await client.get_transaction(7)
    assert "secret" not in repr(exc.value)
    assert "should-not-leak" not in repr(exc.value)


async def test_4xx_with_non_json_body_still_raises(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/transactions/7",
        status_code=502,
        text="<html>nginx</html>",
    )
    with pytest.raises(FireflyAPIError) as exc:
        await client.get_transaction(7)
    assert exc.value.status_code == 502
    assert exc.value.raw_body() == "<html>nginx</html>"


async def test_search_transaction_groups_returns_groups(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{BASE_URL}/api/v1/search/transactions",
            params={"query": "any", "page": 1, "limit": 50},
        ),
        json={
            "data": [
                {
                    "id": 99,
                    "attributes": {
                        "transactions": [
                            {
                                "transaction_journal_id": 200,
                                "type": "withdrawal",
                                "date": "2026-05-08T12:00:00Z",
                                "description": "Test purchase",
                                "amount": "12.34",
                                "external_id": "abc-123",
                            }
                        ]
                    },
                }
            ],
            "meta": {"pagination": {"current_page": 1, "total_pages": 1}},
        },
    )
    page = await client.search_transaction_groups("any")
    assert len(page.data) == 1
    assert page.data[0].attributes.transactions[0].external_id == "abc-123"


async def test_update_transaction_uses_put(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{BASE_URL}/api/v1/transactions/55",
        json={
            "data": {
                "id": 55,
                "attributes": {
                    "transactions": [
                        {
                            "transaction_journal_id": 300,
                            "type": "withdrawal",
                            "date": "2026-05-08T12:00:00Z",
                            "description": "Test purchase",
                            "amount": "12.34",
                            "category_name": "Groceries",
                        }
                    ]
                },
            }
        },
    )
    group = TransactionGroupIn(transactions=[_split()])
    result = await client.update_transaction(55, group)
    assert result.attributes.transactions[0].category_name == "Groceries"


# ---------------------------------------------------------------------------
# Categories / Tags / Accounts
# ---------------------------------------------------------------------------


async def test_create_category_posts_name(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/v1/categories",
        json={"data": {"id": 1, "attributes": {"name": "Groceries"}}},
    )
    cat = await client.create_category("Groceries")
    request = httpx_mock.get_requests()[0]
    assert b'"name":"Groceries"' in request.read().replace(b" ", b"")
    assert cat.name == "Groceries"
    assert cat.id == 1


async def test_list_categories_pagination_parses(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/categories?page=2&limit=25",
        json={
            "data": [
                {"id": 1, "attributes": {"name": "Groceries"}},
                {"id": 2, "attributes": {"name": "Transport"}},
            ],
            "meta": {
                "pagination": {
                    "total": 27,
                    "count": 2,
                    "per_page": 25,
                    "current_page": 2,
                    "total_pages": 2,
                }
            },
        },
    )
    page = await client.list_categories(page=2, limit=25)
    assert [c.name for c in page.data] == ["Groceries", "Transport"]
    assert page.meta.pagination.current_page == 2
    assert page.meta.pagination.total_pages == 2


async def test_create_tag_uses_tag_field(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/api/v1/tags",
        json={"data": {"id": 7, "attributes": {"tag": "weekend"}}},
    )
    tag = await client.create_tag("weekend")
    request = httpx_mock.get_requests()[0]
    assert b'"tag":"weekend"' in request.read().replace(b" ", b"")
    assert tag.tag == "weekend"


async def test_list_accounts(httpx_mock: HTTPXMock, client: FireflyClient) -> None:
    httpx_mock.add_response(
        url=f"{BASE_URL}/api/v1/accounts?page=1&limit=50",
        json={
            "data": [
                {
                    "id": 11,
                    "attributes": {
                        "name": "Checking",
                        "type": "asset",
                        "currency_code": "EUR",
                        "iban": "FR7612345",
                    },
                }
            ],
            "meta": {"pagination": {}},
        },
    )
    page = await client.list_accounts()
    assert page.data[0].name == "Checking"
    assert page.data[0].attributes.currency_code == "EUR"


# ---------------------------------------------------------------------------
# Queries leaf module
# ---------------------------------------------------------------------------


def test_escape_dsl_value_handles_quotes_and_backslash() -> None:
    assert _escape_dsl_value("abc") == "abc"
    assert _escape_dsl_value('a"b') == 'a\\"b'
    assert _escape_dsl_value("a\\b") == "a\\\\b"
    # Combined: backslash escaped first so a quote isn't double-escaped.
    assert _escape_dsl_value('a\\"b') == 'a\\\\\\"b'


async def test_find_by_external_id_returns_none_when_empty(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{BASE_URL}/api/v1/search/transactions",
            params={"query": 'external_id:"abc-123"', "page": 1, "limit": 1},
        ),
        json={"data": [], "meta": {"pagination": {}}},
    )
    result = await find_transaction_by_external_id(client, "abc-123")
    assert result is None
    request = httpx_mock.get_requests()[0]
    assert request.url.params["query"] == 'external_id:"abc-123"'


async def test_find_by_external_id_escapes_quotes(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    """A `"` in the external_id must be escaped, not break the DSL."""
    httpx_mock.add_response(
        url=httpx.URL(
            f"{BASE_URL}/api/v1/search/transactions",
            params={"query": 'external_id:"a\\"b"', "page": 1, "limit": 1},
        ),
        json={"data": [], "meta": {"pagination": {}}},
    )
    result = await find_transaction_by_external_id(client, 'a"b')
    assert result is None


async def test_find_by_external_id_returns_first_match(
    httpx_mock: HTTPXMock, client: FireflyClient
) -> None:
    httpx_mock.add_response(
        url=httpx.URL(
            f"{BASE_URL}/api/v1/search/transactions",
            params={"query": 'external_id:"abc-123"', "page": 1, "limit": 1},
        ),
        json={
            "data": [
                {
                    "id": 99,
                    "attributes": {
                        "transactions": [
                            {
                                "transaction_journal_id": 200,
                                "type": "withdrawal",
                                "date": "2026-05-08T12:00:00Z",
                                "description": "Test purchase",
                                "amount": "12.34",
                                "external_id": "abc-123",
                            }
                        ]
                    },
                }
            ],
            "meta": {"pagination": {"current_page": 1, "total_pages": 1}},
        },
    )
    result = await find_transaction_by_external_id(client, "abc-123")
    assert result is not None
    assert result.external_id == "abc-123"


async def test_find_by_external_id_rejects_empty_input(client: FireflyClient) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        await find_transaction_by_external_id(client, "")
