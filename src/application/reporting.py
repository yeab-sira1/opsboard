"""Reporting use-case orchestrator.

Coordinates :class:`~src.services.ReportJobService`,
:class:`~src.services.AnalyticsService`, and
:class:`~src.services.ExportService` for the report-generation workflow.
"""

from __future__ import annotations

import uuid
from datetime import date

from src.container import Container
from src.models.report_job import ReportJob
from src.models.report_request import ReportRequest, ReportType
from src.services.analytics_service import InventorySummaryRow
from src.services.dashboard_service import SnapshotDashboard


class ReportingApp:
    """Orchestrates report creation, execution, and export.

    Parameters
    ----------
    container:
        A :class:`~src.container.Container` bound to the current session.
    """

    def __init__(self, container: Container) -> None:
        self._c = container

    def create_and_run_report(
        self,
        report_type: ReportType,
        parameters_json: str = "{}",
    ) -> ReportJob:
        """Create a report request, immediately run it, and return the job.

        Parameters
        ----------
        report_type:
            The kind of report to generate.
        parameters_json:
            Optional JSON parameters (e.g. ``{"snapshot_date": "2026-01-01"}``
            for :attr:`~src.models.ReportType.DAILY_SNAPSHOT` reports).
        """
        session = self._c._session  # noqa: SLF001 — container owns the session
        request = ReportRequest(
            report_type=report_type,
            parameters_json=parameters_json,
        )
        session.add(request)
        session.flush()

        job = self._c.report_jobs.create_job(request.id)
        self._c.report_jobs.run_job(job.id)
        return job

    def get_inventory_summary(self) -> list[InventorySummaryRow]:
        """Return the current per-product/warehouse inventory summary."""
        return self._c.analytics.get_inventory_summary()

    def get_snapshot_dashboard(
        self, snapshot_date: date
    ) -> SnapshotDashboard:
        """Return the snapshot dashboard for a given date.

        Parameters
        ----------
        snapshot_date:
            The date whose stored snapshots should be summarised.
        """
        return self._c.dashboard.get_snapshot_dashboard(snapshot_date)

    def export_inventory_csv(self) -> str:
        """Return the current inventory summary as a CSV string."""
        return self._c.export.export_inventory_summary_csv()

    def export_snapshot_csv(self, snapshot_date: date) -> str:
        """Return stored snapshots for ``snapshot_date`` as a CSV string.

        Parameters
        ----------
        snapshot_date:
            The date whose snapshots should be exported.
        """
        return self._c.export.export_daily_snapshot_csv(snapshot_date)
