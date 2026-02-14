"""Repository for :class:`RetryAttempt` persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.retry_attempt import RetryAttempt
from src.repositories.base_repository import BaseRepository


class RetryAttemptRepository(BaseRepository[RetryAttempt]):
    """CRUD operations and lookups for retry attempts."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RetryAttempt)

    def get_by_job(
        self, scheduled_job_id: uuid.UUID
    ) -> list[RetryAttempt]:
        """Return all attempts for a scheduled job, oldest first."""
        return list(
            self._session.scalars(
                select(RetryAttempt)
                .where(RetryAttempt.scheduled_job_id == scheduled_job_id)
                .order_by(RetryAttempt.attempt_number)
            ).all()
        )

    def get_failed_attempts(
        self, scheduled_job_id: uuid.UUID
    ) -> list[RetryAttempt]:
        """Return the unsuccessful attempts for a scheduled job."""
        return list(
            self._session.scalars(
                select(RetryAttempt).where(
                    RetryAttempt.scheduled_job_id == scheduled_job_id,
                    RetryAttempt.successful.is_(False),
                )
            ).all()
        )

    def get_successful_attempts(
        self, scheduled_job_id: uuid.UUID
    ) -> list[RetryAttempt]:
        """Return the successful attempts for a scheduled job."""
        return list(
            self._session.scalars(
                select(RetryAttempt).where(
                    RetryAttempt.scheduled_job_id == scheduled_job_id,
                    RetryAttempt.successful.is_(True),
                )
            ).all()
        )
