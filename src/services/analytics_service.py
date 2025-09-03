"""Analytics service: reporting and aggregation over operational data."""

from __future__ import annotations

import uuid
from datetime import date
from typing import NamedTuple

from sqlalchemy.orm import Session

from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.models.order import OrderStatus
from src.models.reservation import ReservationStatus
from src.repositories import (
    DailyInventorySnapshotRepository,
    ReservationRepository,
    StockRecordRepository,
)
from src.services.inventory_service import InventoryService
from src.services.order_service import OrderService
from src.services.reservation_service import ReservationService


class InventorySummaryRow(NamedTuple):
    """Aggregated stock position for one product at one warehouse."""

    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    physical_stock: int
    reserved_quantity: int
    available_stock: int


class AnalyticsError(Exception):
    """Base class for analytics-related errors."""


class SnapshotAlreadyExistsError(AnalyticsError):
    """Raised when generating snapshots for a date that already has them."""

    def __init__(self, snapshot_date: date) -> None:
        super().__init__(f"Snapshot already exists for date: {snapshot_date}")
        self.snapshot_date = snapshot_date


class SnapshotNotFoundError(AnalyticsError):
    """Raised when a requested snapshot does not exist."""

    def __init__(
        self,
        snapshot_date: date,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> None:
        super().__init__(
            f"Snapshot not found: date={snapshot_date}, "
            f"product={product_id}, warehouse={warehouse_id}"
        )
        self.snapshot_date = snapshot_date
        self.product_id = product_id
        self.warehouse_id = warehouse_id


class AnalyticsService:
    """Produces summaries and snapshots from existing operational services.

    Availability is never recomputed here: physical stock comes from
    :class:`InventoryService` and reserved/available figures come from
    :class:`ReservationService`, keeping a single source of truth.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._inventory = InventoryService(session)
        self._reservations = ReservationService(session)
        self._orders = OrderService(session)
        self._stock = StockRecordRepository(session)
        self._reservation_repo = ReservationRepository(session)
        self._snapshots = DailyInventorySnapshotRepository(session)

    def get_inventory_summary(self) -> list[InventorySummaryRow]:
        """Return per-(product, warehouse) physical/reserved/available stock."""
        rows: list[InventorySummaryRow] = []
        for record in self._stock.list():
            product_id = record.product_id
            warehouse_id = record.warehouse_id
            rows.append(
                InventorySummaryRow(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    physical_stock=self._inventory.get_stock(
                        product_id, warehouse_id
                    ),
                    reserved_quantity=self._reservations.get_reserved_quantity(
                        product_id, warehouse_id
                    ),
                    available_stock=self._reservations.get_available_stock(
                        product_id, warehouse_id
                    ),
                )
            )
        return rows

    def get_order_summary(self) -> dict[OrderStatus, int]:
        """Return order counts keyed by every :class:`OrderStatus`."""
        return {
            status: len(self._orders.get_orders_by_status(status))
            for status in OrderStatus
        }

    def get_reservation_summary(self) -> dict[ReservationStatus, int]:
        """Return reservation counts keyed by every status."""
        counts = {status: 0 for status in ReservationStatus}
        for reservation in self._reservation_repo.list():
            counts[reservation.status] += 1
        return counts

    def generate_daily_snapshot(
        self, snapshot_date: date
    ) -> list[DailyInventorySnapshot]:
        """Persist a snapshot row per (product, warehouse) for ``snapshot_date``.

        Reuses :meth:`get_inventory_summary` so availability figures stay
        consistent with live data. Raises if the date already has snapshots.
        """
        if self._snapshots.get_by_date(snapshot_date):
            raise SnapshotAlreadyExistsError(snapshot_date)

        created: list[DailyInventorySnapshot] = []
        for row in self.get_inventory_summary():
            created.append(
                self._snapshots.add(
                    DailyInventorySnapshot(
                        snapshot_date=snapshot_date,
                        product_id=row.product_id,
                        warehouse_id=row.warehouse_id,
                        physical_stock=row.physical_stock,
                        reserved_quantity=row.reserved_quantity,
                        available_stock=row.available_stock,
                    )
                )
            )
        return created

    def get_snapshot(
        self,
        snapshot_date: date,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
    ) -> DailyInventorySnapshot:
        """Return one snapshot or raise :class:`SnapshotNotFoundError`."""
        for snapshot in self._snapshots.get_by_date(snapshot_date):
            if (
                snapshot.product_id == product_id
                and snapshot.warehouse_id == warehouse_id
            ):
                return snapshot
        raise SnapshotNotFoundError(snapshot_date, product_id, warehouse_id)

    def get_snapshots_by_date(
        self, snapshot_date: date
    ) -> list[DailyInventorySnapshot]:
        """Return all snapshots recorded on ``snapshot_date``."""
        return self._snapshots.get_by_date(snapshot_date)
