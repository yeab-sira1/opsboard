"""Repository for :class:`DomainEvent` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.domain_event import DomainEvent, DomainEventType
from src.repositories.base_repository import BaseRepository


class DomainEventRepository(BaseRepository[DomainEvent]):
    """CRUD operations and lookups for domain events."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DomainEvent)

    def get_by_event_type(
        self, event_type: DomainEventType
    ) -> list[DomainEvent]:
        """Return all events of the given ``event_type``."""
        return list(
            self._session.scalars(
                select(DomainEvent).where(
                    DomainEvent.event_type == event_type
                )
            ).all()
        )

    def get_recent(self, limit: int = 10) -> list[DomainEvent]:
        """Return the most recently recorded events, newest first."""
        return list(
            self._session.scalars(
                select(DomainEvent)
                .order_by(DomainEvent.created_at.desc())
                .limit(limit)
            ).all()
        )
