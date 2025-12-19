"""Dashboard service: structured read models for UI dashboards."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.models.order import OrderStatus
from src.models.reservation import ReservationStatus
from src.services.analytics_service import AnalyticsService, InventorySummaryRow
from src.services.cache_service import CacheService


@dataclass(frozen=True)
class InventoryDashboard:
    """Inventory rows plus dashboard-level totals."""

    rows: list[InventorySummaryRow]
    total_physical: int
    total_reserved: int
    total_available: int


@dataclass(frozen=True)
class OrderDashboard:
    """Order counts by status plus the overall order total."""

    counts: dict[OrderStatus, int]
    total_orders: int


@dataclass(frozen=True)
class ReservationDashboard:
    """Reservation counts by status plus the overall reservation total."""

    counts: dict[ReservationStatus, int]
    total_reservations: int


@dataclass(frozen=True)
class SnapshotDashboard:
    """Snapshot rows for a date plus their total available stock."""

    snapshot_date: date
    rows: list[DailyInventorySnapshot]
    total_available: int


class DashboardService:
    """Builds structured dashboard views from :class:`AnalyticsService`.

    Aggregation lives entirely in the analytics layer; this service only
    arranges the results and derives presentation-level totals.
    """

    def __init__(
        self, session: Session, cache: CacheService | None = None
    ) -> None:
        self._analytics = AnalyticsService(session)
        self._cache = cache

    def get_inventory_dashboard(self) -> InventoryDashboard:
        """Return inventory rows with physical/reserved/available totals."""
        rows = self._analytics.get_inventory_summary()
        return InventoryDashboard(
            rows=rows,
            total_physical=sum(row.physical_stock for row in rows),
            total_reserved=sum(row.reserved_quantity for row in rows),
            total_available=sum(row.available_stock for row in rows),
        )

    def get_order_dashboard(self) -> OrderDashboard:
        """Return order counts by status with the overall total.

        The status/count map is cached when a cache is configured.
        """
        counts = self._cached_counts(
            "dashboard:order_counts",
            lambda: {
                status.value: count
                for status, count in self._analytics.get_order_summary().items()
            },
        )
        counts = {OrderStatus(value): count for value, count in counts.items()}
        return OrderDashboard(counts=counts, total_orders=sum(counts.values()))

    def get_reservation_dashboard(self) -> ReservationDashboard:
        """Return reservation counts by status with the overall total.

        The status/count map is cached when a cache is configured.
        """
        counts = self._cached_counts(
            "dashboard:reservation_counts",
            lambda: {
                status.value: count
                for status, count in (
                    self._analytics.get_reservation_summary().items()
                )
            },
        )
        counts = {
            ReservationStatus(value): count for value, count in counts.items()
        }
        return ReservationDashboard(
            counts=counts, total_reservations=sum(counts.values())
        )

    def _cached_counts(
        self, cache_key: str, builder: "Callable[[], dict[str, int]]"
    ) -> dict[str, int]:
        if self._cache is None:
            return builder()
        return self._cache.get_or_set(cache_key, builder)

    def get_snapshot_dashboard(
        self, snapshot_date: date
    ) -> SnapshotDashboard:
        """Return stored snapshots for ``snapshot_date`` with availability."""
        rows = self._analytics.get_snapshots_by_date(snapshot_date)
        return SnapshotDashboard(
            snapshot_date=snapshot_date,
            rows=rows,
            total_available=sum(row.available_stock for row in rows),
        )
