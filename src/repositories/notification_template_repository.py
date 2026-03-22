"""Repository for :class:`NotificationTemplate` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.notification_template import NotificationTemplate
from src.repositories.base_repository import BaseRepository


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """CRUD operations and lookups for notification templates."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NotificationTemplate)

    def get_by_name(self, name: str) -> NotificationTemplate | None:
        """Return the template with ``name`` or ``None`` if absent."""
        return self._session.scalar(
            select(NotificationTemplate).where(
                NotificationTemplate.name == name
            )
        )
