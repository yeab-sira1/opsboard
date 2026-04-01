"""Repository for :class:`AuditEntry` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_entry import AuditEntry
from src.repositories.base_repository import BaseRepository


class AuditEntryRepository(BaseRepository[AuditEntry]):
    """CRUD operations and lookups for audit entries."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, AuditEntry)

    def get_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[AuditEntry]:
        """Return all entries for one entity, oldest first."""
        return list(
            self._session.scalars(
                select(AuditEntry)
                .where(
                    AuditEntry.entity_type == entity_type,
                    AuditEntry.entity_id == entity_id,
                )
                .order_by(AuditEntry.created_at)
            ).all()
        )

    def get_by_action(self, action: str) -> list[AuditEntry]:
        """Return all entries recording the given ``action``, oldest first."""
        return list(
            self._session.scalars(
                select(AuditEntry)
                .where(AuditEntry.action == action)
                .order_by(AuditEntry.created_at)
            ).all()
        )

    def get_recent(self, limit: int = 10) -> list[AuditEntry]:
        """Return the most recently created entries, newest first."""
        return list(
            self._session.scalars(
                select(AuditEntry)
                .order_by(AuditEntry.created_at.desc())
                .limit(limit)
            ).all()
        )
