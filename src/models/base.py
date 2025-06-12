"""Declarative base and shared column mixins for opsboard models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC ``datetime``."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all opsboard ORM models."""


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID ``id`` primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Mixin that adds a timezone-aware ``created_at`` column."""

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
