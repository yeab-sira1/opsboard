"""Batch export service for exporting multiple reports as CSV."""

from __future__ import annotations

from src.schemas import BatchReportRequest
from src.services import ExportService


class BatchExportService:
    """Exports multiple reports as CSV in a batch."""

    def __init__(self, export_service: ExportService) -> None:
        self._export = export_service

    def export_batch_csv(
        self, request: BatchReportRequest
    ) -> dict[str, str]:
        """Export a batch of reports as CSV strings."""
        if request.is_empty():
            return {}

        results = {}

        for item in request.items:
            try:
                if item.report_type == "inventory":
                    csv_data = self.export_inventory_batch()
                elif item.report_type == "orders":
                    csv_data = self.export_order_batch()
                elif item.report_type == "reservations":
                    csv_data = self.export_reservation_batch()
                else:
                    raise ValueError(f"Unknown report type: {item.report_type}")

                results[item.report_type] = csv_data
            except Exception as e:
                results[item.report_type] = f"Error: {str(e)}"

        return results

    def export_inventory_batch(self) -> str:
        """Export inventory as CSV."""
        return self._export.export_inventory_summary_csv()

    def export_order_batch(self) -> str:
        """Export orders as CSV."""
        return self._export.export_order_summary_csv()

    def export_reservation_batch(self) -> str:
        """Export reservations as CSV."""
        return self._export.export_reservation_summary_csv()
