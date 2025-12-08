"""Repository for :class:`CacheEntry` persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.cache_entry import CacheEntry
from src.repositories.base_repository import BaseRepository


class CacheRepository(BaseRepository[CacheEntry]):
    """CRUD operations and key/expiry lookups for cache entries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CacheEntry)

    def get_by_key(self, cache_key: str) -> CacheEntry | None:
        """Return the entry for ``cache_key`` or ``None`` if absent."""
        return self._session.scalar(
            select(CacheEntry).where(CacheEntry.cache_key == cache_key)
        )

    def get_expired(self, now: datetime) -> list[CacheEntry]:
        """Return entries whose ``expires_at`` is at or before ``now``.

        Entries without an expiry (``expires_at IS NULL``) are never returned.
        """
        return list(
            self._session.scalars(
                select(CacheEntry).where(
                    CacheEntry.expires_at.is_not(None),
                    CacheEntry.expires_at <= now,
                )
            ).all()
        )

    def delete_by_key(self, cache_key: str) -> bool:
        """Delete the entry for ``cache_key``; return whether one was removed."""
        entry = self.get_by_key(cache_key)
        if entry is None:
            return False
        self.delete(entry)
        return True
