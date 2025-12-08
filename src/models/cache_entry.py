"""Cache entry model: a persisted key/value cache record."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CacheEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single cached value addressed by a unique key.

    ``payload_json`` holds the serialized value. ``expires_at`` is optional; a
    null value means the entry never expires. Expiry is interpreted by the
    cache service, not enforced at the storage layer.
    """

    __tablename__ = "cache_entries"

    cache_key: Mapped[str] = mapped_column(String(255), unique=True)
    payload_json: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)

    def __repr__(self) -> str:
        return (
            f"CacheEntry(id={self.id!r}, cache_key={self.cache_key!r}, "
            f"expires_at={self.expires_at!r})"
        )
