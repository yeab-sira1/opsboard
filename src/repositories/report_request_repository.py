"""Repository for :class:`ReportRequest` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.report_request import ReportRequest, ReportType
from src.repositories.base_repository import BaseRepository


class ReportRequestRepository(BaseRepository[ReportRequest]):
    """CRUD operations and lookups for report requests."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ReportRequest)

    def get_by_report_type(
        self, report_type: ReportType
    ) -> list[ReportRequest]:
        """Return all requests of the given ``report_type``."""
        return list(
            self._session.scalars(
                select(ReportRequest).where(
                    ReportRequest.report_type == report_type
                )
            ).all()
        )

    def get_recent(self, limit: int = 10) -> list[ReportRequest]:
        """Return the most recently requested reports, newest first."""
        return list(
            self._session.scalars(
                select(ReportRequest)
                .order_by(ReportRequest.requested_at.desc())
                .limit(limit)
            ).all()
        )
