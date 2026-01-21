"""Report bundle repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import ReportBundle


class ReportBundleRepository:
    """Repository for report bundle persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, bundle: ReportBundle) -> ReportBundle:
        """Add and persist a report bundle."""
        self._session.add(bundle)
        self._session.flush()
        return bundle

    def get(self, bundle_id) -> ReportBundle | None:
        """Get a bundle by ID."""
        return self._session.get(ReportBundle, bundle_id)

    def get_by_name(self, bundle_name: str) -> ReportBundle | None:
        """Get a bundle by name."""
        stmt = select(ReportBundle).where(
            ReportBundle.bundle_name == bundle_name
        )
        return self._session.scalars(stmt).first()

    def get_recent(self, limit: int = 10) -> list[ReportBundle]:
        """Get recent bundles ordered by creation date."""
        stmt = (
            select(ReportBundle)
            .order_by(ReportBundle.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def list(self) -> list[ReportBundle]:
        """Get all bundles."""
        return list(self._session.scalars(select(ReportBundle)).all())
