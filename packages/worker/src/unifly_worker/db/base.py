"""SQLAlchemy declarative base + naming convention.

Centralising the metadata here keeps Alembic autogenerate stable: every model
inherits from :class:`Base`, so ``Base.metadata`` is the single source of truth
for both runtime sessions and migration generation.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Stable, predictable constraint names — required for Alembic to emit safe
# DROP CONSTRAINT statements on downgrades.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
