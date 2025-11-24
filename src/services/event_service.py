"""Event service: persistence of domain events."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from src.models.domain_event import DomainEvent, DomainEventType
from src.repositories import DomainEventRepository


class EventService:
    """Records and retrieves domain events.

    This layer is persistence-only: events are stored as an audit trail and no
    dispatching or subscriber notification occurs.
    """

    def __init__(self, session: Session) -> None:
        self._events = DomainEventRepository(session)

    def record_event(
        self,
        event_type: DomainEventType,
        payload: dict[str, Any] | None = None,
    ) -> DomainEvent:
        """Persist an event of ``event_type`` with an optional JSON payload."""
        return self._events.add(
            DomainEvent(
                event_type=event_type,
                payload_json=json.dumps(payload or {}),
            )
        )

    def get_events_by_type(
        self, event_type: DomainEventType
    ) -> list[DomainEvent]:
        """Return all events of the given ``event_type``."""
        return self._events.get_by_event_type(event_type)

    def get_recent_events(self, limit: int = 10) -> list[DomainEvent]:
        """Return the most recently recorded events, newest first."""
        return self._events.get_recent(limit)
