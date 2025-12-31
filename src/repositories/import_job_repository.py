"""Repository for :class:`ImportJob` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.import_job import ImportJob, ImportJobStatus
from src.repositories.base_repository import BaseRepository


class ImportJobRepository(BaseRepository[ImportJob]):
    """CRUD operations and lookups for import jobs."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ImportJob)

    def get_by_status(self, status: ImportJobStatus) -> list[ImportJob]:
        """Return all import jobs in the given ``status``."""
        return list(
            self._session.scalars(
                select(ImportJob).where(ImportJob.status == status)
            ).all()
        )

    def get_recent(self, limit: int = 10) -> list[ImportJob]:
        """Return the most recently created import jobs, newest first."""
        return list(
            self._session.scalars(
                select(ImportJob)
                .order_by(ImportJob.created_at.desc())
                .limit(limit)
            ).all()
        )
