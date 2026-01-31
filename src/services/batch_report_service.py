"""Batch report service for generating multiple reports."""

from __future__ import annotations

from src.schemas import BatchReportRequest, BatchReportResult
from src.services import (
    AnalyticsService,
    DashboardService,
)


class BatchReportService:
    """Generates multiple reports in a batch."""

    def __init__(
        self,
        dashboard_service: DashboardService,
        analytics_service: AnalyticsService,
    ) -> None:
        self._dashboard = dashboard_service
        self._analytics = analytics_service

    def generate_batch_reports(
        self, request: BatchReportRequest
    ) -> BatchReportResult:
        """Generate a batch of reports."""
        if request.is_empty():
            return BatchReportResult(results={}, generated_count=0, failed_count=0)

        results = {}
        generated_count = 0
        failed_count = 0

        for item in request.items:
            try:
                if item.report_type == "inventory":
                    report = self.generate_inventory_batch()
                elif item.report_type == "orders":
                    report = self.generate_order_batch()
                elif item.report_type == "reservations":
                    report = self.generate_reservation_batch()
                else:
                    raise ValueError(f"Unknown report type: {item.report_type}")

                results[item.report_type] = report
                generated_count += 1
            except Exception as e:
                results[item.report_type] = {"error": str(e)}
                failed_count += 1

        return BatchReportResult(
            results=results,
            generated_count=generated_count,
            failed_count=failed_count,
        )

    def generate_inventory_batch(self) -> dict:
        """Generate inventory summary report."""
        dashboard = self._dashboard.get_inventory_dashboard()
        return {
            "total_rows": len(dashboard.rows) if dashboard.rows else 0,
            "total_physical": dashboard.total_physical,
            "total_reserved": dashboard.total_reserved,
            "total_available": dashboard.total_available,
        }

    def generate_order_batch(self) -> dict:
        """Generate orders summary report."""
        dashboard = self._dashboard.get_order_dashboard()
        return {
            "total_orders": dashboard.total_orders,
            "counts": dashboard.counts,
        }

    def generate_reservation_batch(self) -> dict:
        """Generate reservations summary report."""
        dashboard = self._dashboard.get_reservation_dashboard()
        return {
            "total_reservations": dashboard.total_reservations,
            "counts": dashboard.counts,
        }
