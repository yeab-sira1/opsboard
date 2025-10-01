"""Export service: CSV serialization of analytics results."""

from __future__ import annotations

import csv
import io
from datetime import date

from sqlalchemy.orm import Session

from src.models.order import OrderStatus
from src.models.reservation import ReservationStatus
from src.services.analytics_service import AnalyticsService


class ExportService:
    """Serializes :class:`AnalyticsService` results to CSV strings.

    Aggregation lives in the analytics layer; this service only formats the
    results. CSV is produced in-memory with the standard library ``csv``
    module — no files are written.
    """

    def __init__(self, session: Session) -> None:
        self._analytics = AnalyticsService(session)

    @staticmethod
    def _new_writer() -> tuple[io.StringIO, "csv._writer"]:
        buffer = io.StringIO()
        return buffer, csv.writer(buffer, lineterminator="\n")

    def export_inventory_summary_csv(self) -> str:
        """Return inventory summary rows as CSV."""
        buffer, writer = self._new_writer()
        writer.writerow(
            [
                "product_id",
                "warehouse_id",
                "physical_stock",
                "reserved_quantity",
                "available_stock",
            ]
        )
        for row in self._analytics.get_inventory_summary():
            writer.writerow(
                [
                    str(row.product_id),
                    str(row.warehouse_id),
                    row.physical_stock,
                    row.reserved_quantity,
                    row.available_stock,
                ]
            )
        return buffer.getvalue()

    def export_order_summary_csv(self) -> str:
        """Return order counts by status as CSV."""
        buffer, writer = self._new_writer()
        writer.writerow(["status", "count"])
        summary = self._analytics.get_order_summary()
        for status in OrderStatus:
            writer.writerow([status.value, summary[status]])
        return buffer.getvalue()

    def export_reservation_summary_csv(self) -> str:
        """Return reservation counts by status as CSV."""
        buffer, writer = self._new_writer()
        writer.writerow(["status", "count"])
        summary = self._analytics.get_reservation_summary()
        for status in ReservationStatus:
            writer.writerow([status.value, summary[status]])
        return buffer.getvalue()

    def export_daily_snapshot_csv(self, snapshot_date: date) -> str:
        """Return stored snapshots for ``snapshot_date`` as CSV."""
        buffer, writer = self._new_writer()
        writer.writerow(
            [
                "snapshot_date",
                "product_id",
                "warehouse_id",
                "physical_stock",
                "reserved_quantity",
                "available_stock",
            ]
        )
        for row in self._analytics.get_snapshots_by_date(snapshot_date):
            writer.writerow(
                [
                    row.snapshot_date.isoformat(),
                    str(row.product_id),
                    str(row.warehouse_id),
                    row.physical_stock,
                    row.reserved_quantity,
                    row.available_stock,
                ]
            )
        return buffer.getvalue()
