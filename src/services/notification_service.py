"""Notification service: lifecycle management for notifications."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.models.notification import Notification, NotificationStatus
from src.repositories import NotificationRepository
from src.models.base import utcnow


class NotificationError(Exception):
    """Base class for notification-related errors."""


class NotificationNotFoundError(NotificationError):
    """Raised when a referenced notification does not exist."""

    def __init__(self, notification_id: uuid.UUID) -> None:
        super().__init__(f"Notification not found: {notification_id}")
        self.notification_id = notification_id


class InvalidNotificationStateError(NotificationError):
    """Raised when an operation is invalid for the current status."""

    def __init__(
        self, notification_id: uuid.UUID, status: NotificationStatus
    ) -> None:
        super().__init__(
            f"Invalid notification state for operation: "
            f"notification={notification_id}, status={status.name}"
        )
        self.notification_id = notification_id
        self.status = status


class NotificationService:
    """Creates notifications and drives their delivery lifecycle.

    Notifications are created ``PENDING`` and transition once to either
    ``SENT`` or ``FAILED``; no transport is performed.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._notifications = NotificationRepository(session)

    def create_notification(self, subject: str, body: str) -> Notification:
        """Create and persist a new ``PENDING`` notification."""
        return self._notifications.add(
            Notification(
                subject=subject,
                body=body,
                status=NotificationStatus.PENDING,
            )
        )

    def mark_sent(self, notification_id: uuid.UUID) -> Notification:
        """Transition a pending notification to ``SENT``."""
        notification = self._require_notification(notification_id)
        self._require_pending(notification)
        notification.status = NotificationStatus.SENT
        notification.sent_at = utcnow()
        self._session.flush()
        return notification

    def mark_failed(self, notification_id: uuid.UUID) -> Notification:
        """Transition a pending notification to ``FAILED``."""
        notification = self._require_notification(notification_id)
        self._require_pending(notification)
        notification.status = NotificationStatus.FAILED
        self._session.flush()
        return notification

    def get_notifications_by_status(
        self, status: NotificationStatus
    ) -> list[Notification]:
        """Return all notifications in the given ``status``."""
        return self._notifications.get_by_status(status)

    def _require_notification(
        self, notification_id: uuid.UUID
    ) -> Notification:
        notification = self._notifications.get(notification_id)
        if notification is None:
            raise NotificationNotFoundError(notification_id)
        return notification

    @staticmethod
    def _require_pending(notification: Notification) -> None:
        if notification.status is not NotificationStatus.PENDING:
            raise InvalidNotificationStateError(
                notification.id, notification.status
            )
