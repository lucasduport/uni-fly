"""Companion database package.

Public surface kept intentionally tight: import from
:mod:`unifly_worker.db.models`, :mod:`unifly_worker.db.session`, or
:mod:`unifly_worker.db.base` directly so internal moves don't break consumers.

Only :class:`Base` is re-exported because Alembic and migration tools always
need it.
"""

from unifly_worker.db.base import Base

__all__ = ["Base"]
