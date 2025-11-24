"""Repository for :class:`ScheduledJob` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from src.repositories.base_repository import BaseRepository


class ScheduledJobRepository(BaseRepository[ScheduledJob]):
    """CRUD operations and status lookups for scheduled jobs."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ScheduledJob)

    def get_by_status(
        self, status: ScheduledJobStatus
    ) -> list[ScheduledJob]:
        """Return all scheduled jobs in the given ``status``."""
        return list(
            self._session.scalars(
                select(ScheduledJob).where(ScheduledJob.status == status)
            ).all()
        )

    def get_pending_jobs(self) -> list[ScheduledJob]:
        """Return all scheduled jobs awaiting execution."""
        return self.get_by_status(ScheduledJobStatus.PENDING)
