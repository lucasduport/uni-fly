"""High-level Firefly III query helpers — the *opinionated* leaf.

Holds the search-DSL dialect and convenience composers built on top of
:class:`FireflyClient`. Activities consume these helpers; the transport
client itself stays neutral about how callers shape queries.
"""

from __future__ import annotations

import logging

from unifly_worker.clients.firefly.client import FireflyClient
from unifly_worker.clients.firefly.models import TransactionRead

logger = logging.getLogger(__name__)


def _escape_dsl_value(value: str) -> str:
    """Escape ``\\`` then ``"`` so a value can be embedded in ``field:"..."``.

    Firefly's search DSL is Lucene-ish — backslash escapes a literal quote.
    Without escaping, a ``"`` in the value closes the term and lets the rest
    be re-interpreted as DSL (a robustness bug, not currently exploitable
    via untrusted input but defended in depth).
    """
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def find_transaction_by_external_id(
    client: FireflyClient, external_id: str
) -> TransactionRead | None:
    """Return the first transaction with ``external_id`` or ``None``.

    Firefly III's ``external_id`` is global (not per-account) and there is no
    dedicated lookup endpoint, so we go via the search DSL. Result groups are
    flattened to splits — callers care about the transaction line, not the
    group envelope.
    """
    if not external_id:
        msg = "external_id must be a non-empty string"
        raise ValueError(msg)
    quoted = _escape_dsl_value(external_id)
    query = f'external_id:"{quoted}"'
    logger.debug("Searching Firefly by external_id (escaped) query=%s", query)
    page = await client.search_transaction_groups(query, page=1, limit=1)
    for group in page.data:
        for split in group.attributes.transactions:
            return split
    return None
