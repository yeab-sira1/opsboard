"""Repository for :class:`ReportJob` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.report_job import ReportJob, ReportJobStatus
from src.repositories.base_repository import BaseRepository


class ReportJobRepository(BaseRepository[ReportJob]):
    """CRUD operations and status lookups for report jobs."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ReportJob)

    def get_by_status(self, status: ReportJobStatus) -> list[ReportJob]:
        """Return all jobs in the given ``status``."""
        return list(
            self._session.scalars(
                select(ReportJob).where(ReportJob.status == status)
            ).all()
        )

    def get_pending_jobs(self) -> list[ReportJob]:
        """Return all jobs awaiting execution."""
        return self.get_by_status(ReportJobStatus.PENDING)
