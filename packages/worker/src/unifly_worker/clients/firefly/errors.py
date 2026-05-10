"""Exceptions raised by the Firefly III client.

The raw response body is kept available for debugging but stored under a
private name (``_body``) and excluded from ``__repr__`` so that structured
logging tools (Sentry, structlog) don't accidentally serialize potentially
sensitive Firefly response payloads. Use :meth:`raw_body` explicitly when
you really need it.
"""

from __future__ import annotations


class FireflyAPIError(Exception):
    """Raised on any non-2xx response from Firefly III."""

    def __init__(
        self,
        status_code: int,
        body: dict[str, object] | str,
        message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.message = message or self._extract_message(body) or "Firefly III API error"
        super().__init__(f"[{status_code}] {self.message}")

    def raw_body(self) -> dict[str, object] | str:
        """Return the underlying response body. Avoid logging the result."""
        return self._body

    def __repr__(self) -> str:
        # Deliberately omit body — exception reprs land in many places.
        return f"{type(self).__name__}(status_code={self.status_code}, message={self.message!r})"

    @staticmethod
    def _extract_message(body: dict[str, object] | str) -> str | None:
        if isinstance(body, dict):
            value = body.get("message")
            if isinstance(value, str):
                return value
        return None


class FireflyValidationError(FireflyAPIError):
    """Raised on HTTP 422 from Firefly III.

    Attributes:
        errors: Mapping of dotted field paths to a list of validation messages
            as returned by Firefly III (e.g. ``{"transactions.0.description":
            ["The description field is required."]}``).
    """

    def __init__(self, body: dict[str, object]) -> None:
        errors_raw = body.get("errors", {})
        if isinstance(errors_raw, dict):
            self.errors: dict[str, list[str]] = {
                k: [str(item) for item in v] for k, v in errors_raw.items() if isinstance(v, list)
            }
        else:
            self.errors = {}
        super().__init__(status_code=422, body=body)
