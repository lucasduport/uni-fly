"""Pydantic models for the Firefly III v1 REST API.

Only the fields the worker actually reads or writes are modelled. Frozen so
returned values can't be mutated by callers — keeps activity logic side-effect
free per project coding standards.

The wire models are intentionally **unopinionated**: they describe the shape
of what Firefly accepts, not how callers should fill it. Defaults like
``apply_rules`` live on the activities/leaf modules that build these objects,
not here.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TransactionType = Literal["withdrawal", "deposit", "transfer"]


class _Frozen(BaseModel):
    """Base model: frozen, allows population by alias."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TransactionSplitIn(_Frozen):
    """A single split inside a transaction group on create/update."""

    type: TransactionType
    date: datetime
    amount: Decimal
    description: str

    source_id: int | None = None
    source_name: str | None = None
    destination_id: int | None = None
    destination_name: str | None = None

    external_id: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] | None = None
    notes: str | None = None

    # Required only when updating an existing split via PUT — otherwise Firefly
    # treats unknown splits as new and deletes the others.
    transaction_journal_id: int | None = None


class TransactionGroupIn(_Frozen):
    """POST/PUT body wrapper Firefly III requires for transaction groups.

    ``apply_rules`` and ``error_if_duplicate_hash`` are intentionally
    ``None`` by default and stripped via ``exclude_none`` at serialization
    time, so this DTO doesn't bake in a workflow policy. Callers (sync,
    reclassify, manual import) decide explicitly.
    """

    transactions: list[TransactionSplitIn]
    apply_rules: bool | None = None
    error_if_duplicate_hash: bool | None = None


class TransactionRead(_Frozen):
    """A single split as returned by Firefly III (subset of fields)."""

    transaction_journal_id: int | None = None
    type: TransactionType
    date: datetime
    description: str
    amount: Decimal

    external_id: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    tags: list[str] = Field(default_factory=list)


class TransactionGroupAttributes(_Frozen):
    transactions: list[TransactionRead]


class TransactionGroupRead(_Frozen):
    """Top-level transaction object returned under ``data``."""

    id: int
    attributes: TransactionGroupAttributes


# ---------------------------------------------------------------------------
# Categories / Tags / Accounts
# ---------------------------------------------------------------------------


class _Resource(_Frozen):
    """Common ``{ "id": str, "attributes": {...} }`` envelope shape."""

    id: int


class CategoryAttributes(_Frozen):
    name: str


class Category(_Resource):
    attributes: CategoryAttributes

    @property
    def name(self) -> str:
        return self.attributes.name


class TagAttributes(_Frozen):
    tag: str


class Tag(_Resource):
    attributes: TagAttributes

    @property
    def tag(self) -> str:
        return self.attributes.tag


class AccountAttributes(_Frozen):
    name: str
    type: str
    currency_code: str | None = None
    iban: str | None = None
    account_number: str | None = None


class Account(_Resource):
    attributes: AccountAttributes

    @property
    def name(self) -> str:
        return self.attributes.name


# ---------------------------------------------------------------------------
# Pagination envelope
# ---------------------------------------------------------------------------


class PaginationMeta(_Frozen):
    total: int = 0
    count: int = 0
    per_page: int = 0
    current_page: int = 1
    total_pages: int = 1


class Meta(_Frozen):
    pagination: PaginationMeta = Field(default_factory=PaginationMeta)


class Page[T: BaseModel](_Frozen):
    """List response wrapper: ``{ "data": [...], "meta": { "pagination": {...}}}``."""

    data: list[T]
    meta: Meta = Field(default_factory=Meta)


class Single[T: BaseModel](_Frozen):
    """Single-resource response wrapper: ``{ "data": {...} }``."""

    data: T
