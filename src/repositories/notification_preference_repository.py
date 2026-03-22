"""Repository for :class:`NotificationPreference` persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.notification_preference import NotificationPreference
from src.repositories.base_repository import BaseRepository


class NotificationPreferenceRepository(
    BaseRepository[NotificationPreference]
):
    """CRUD operations and lookups for notification preferences."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, NotificationPreference)

    def get_enabled(self) -> list[NotificationPreference]:
        """Return all enabled preferences."""
        return list(
            self._session.scalars(
                select(NotificationPreference).where(
                    NotificationPreference.enabled.is_(True)
                )
            ).all()
        )

    def get_by_category(
        self, category_id: uuid.UUID
    ) -> NotificationPreference | None:
        """Return the preference for ``category_id`` or ``None`` if absent."""
        return self._session.scalar(
            select(NotificationPreference).where(
                NotificationPreference.category_id == category_id
            )
        )
