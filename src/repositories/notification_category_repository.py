"""Repository for :class:`NotificationCategory` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.notification_category import NotificationCategory
from src.repositories.base_repository import BaseRepository


class NotificationCategoryRepository(BaseRepository[NotificationCategory]):
    """CRUD operations and lookups for notification categories."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NotificationCategory)

    def get_by_name(self, name: str) -> NotificationCategory | None:
        """Return the category with ``name`` or ``None`` if absent."""
        return self._session.scalar(
            select(NotificationCategory).where(
                NotificationCategory.name == name
            )
        )
