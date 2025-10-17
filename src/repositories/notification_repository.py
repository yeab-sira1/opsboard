"""Repository for :class:`Notification` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.notification import Notification, NotificationStatus
from src.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """CRUD operations and status lookups for notifications."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Notification)

    def get_by_status(
        self, status: NotificationStatus
    ) -> list[Notification]:
        """Return all notifications in the given ``status``."""
        return list(
            self._session.scalars(
                select(Notification).where(Notification.status == status)
            ).all()
        )

    def get_pending_notifications(self) -> list[Notification]:
        """Return all notifications awaiting delivery."""
        return self.get_by_status(NotificationStatus.PENDING)
