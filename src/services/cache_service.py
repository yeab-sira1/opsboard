"""Cache service: a deterministic, in-memory-style JSON cache.

Values are serialized to JSON and stored as :class:`CacheEntry` rows. Time is
supplied by an injectable ``clock`` so expiry is fully deterministic and never
depends on wall-clock sleeps.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.exceptions.base import OpsboardError
from src.exceptions.validation import ValidationError
from src.models.base import utcnow
from src.models.cache_entry import CacheEntry
from src.repositories import CacheRepository


def _as_aware_utc(value: datetime) -> datetime:
    """Treat a naive datetime as UTC; pass aware datetimes through.

    SQLite drops tzinfo on persistence, so stored timestamps round-trip as
    naive. All opsboard timestamps are written in UTC, so a missing tzinfo can
    be safely interpreted as UTC for comparison.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class CacheError(OpsboardError):
    """Base class for cache-related errors."""


class CacheSerializationError(CacheError, ValidationError):
    """Raised when a value cannot be serialized to JSON."""

    def __init__(self, cache_key: str) -> None:
        super().__init__(f"Value for cache key is not JSON-serializable: {cache_key}")
        self.cache_key = cache_key


class CacheService:
    """Reads and writes JSON-serializable values keyed by string.

    Missing keys and expired entries both read as ``None``. Expiry is lazy:
    expired entries are ignored on read and removed in bulk by
    :meth:`clear_expired`; there is no automatic invalidation on write.
    """

    def __init__(
        self, session: Session, clock: Callable[[], Any] = utcnow
    ) -> None:
        self._session = session
        self._entries = CacheRepository(session)
        self._clock = clock

    def set(
        self, cache_key: str, value: Any, ttl_seconds: int | None = None
    ) -> CacheEntry:
        """Store ``value`` under ``cache_key``, overwriting any existing entry.

        ``ttl_seconds`` sets a relative expiry; ``None`` means no expiry.
        """
        try:
            payload = json.dumps(value)
        except TypeError as exc:
            raise CacheSerializationError(cache_key) from exc

        expires_at = (
            self._clock() + timedelta(seconds=ttl_seconds)
            if ttl_seconds is not None
            else None
        )

        entry = self._entries.get_by_key(cache_key)
        if entry is None:
            return self._entries.add(
                CacheEntry(
                    cache_key=cache_key,
                    payload_json=payload,
                    expires_at=expires_at,
                )
            )
        entry.payload_json = payload
        entry.expires_at = expires_at
        self._session.flush()
        return entry

    def get(self, cache_key: str) -> Any | None:
        """Return the cached value, or ``None`` if missing or expired."""
        entry = self._entries.get_by_key(cache_key)
        if entry is None or self._is_expired(entry):
            return None
        return json.loads(entry.payload_json)

    def exists(self, cache_key: str) -> bool:
        """Return whether a live (non-expired) entry exists for ``cache_key``."""
        entry = self._entries.get_by_key(cache_key)
        return entry is not None and not self._is_expired(entry)

    def delete(self, cache_key: str) -> bool:
        """Delete ``cache_key``; return whether an entry was removed."""
        return self._entries.delete_by_key(cache_key)

    def clear_expired(self) -> int:
        """Remove all expired entries; return how many were removed."""
        expired = self._entries.get_expired(self._clock())
        for entry in expired:
            self._entries.delete(entry)
        return len(expired)

    def get_or_set(
        self,
        cache_key: str,
        producer: Callable[[], Any],
        ttl_seconds: int | None = None,
    ) -> Any:
        """Return the cached value, or compute, store, and return it.

        ``producer`` is only invoked on a cache miss, making this the canonical
        way to wrap an expensive read.
        """
        if self.exists(cache_key):
            return self.get(cache_key)
        value = producer()
        self.set(cache_key, value, ttl_seconds)
        return value

    def _is_expired(self, entry: CacheEntry) -> bool:
        if entry.expires_at is None:
            return False
        return _as_aware_utc(entry.expires_at) <= _as_aware_utc(self._clock())
