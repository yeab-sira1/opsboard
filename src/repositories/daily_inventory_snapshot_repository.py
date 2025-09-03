"""Repository for :class:`DailyInventorySnapshot` persistence."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.daily_inventory_snapshot import DailyInventorySnapshot
from src.repositories.base_repository import BaseRepository


class DailyInventorySnapshotRepository(BaseRepository[DailyInventorySnapshot]):
    """CRUD operations and lookups for daily inventory snapshots."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DailyInventorySnapshot)

    def get_by_date(
        self, snapshot_date: date
    ) -> list[DailyInventorySnapshot]:
        """Return all snapshots taken on ``snapshot_date``."""
        return list(
            self._session.scalars(
                select(DailyInventorySnapshot).where(
                    DailyInventorySnapshot.snapshot_date == snapshot_date
                )
            ).all()
        )

    def get_by_product(
        self, product_id: uuid.UUID
    ) -> list[DailyInventorySnapshot]:
        """Return all snapshots for ``product_id`` across dates/warehouses."""
        return list(
            self._session.scalars(
                select(DailyInventorySnapshot).where(
                    DailyInventorySnapshot.product_id == product_id
                )
            ).all()
        )

    def get_by_warehouse(
        self, warehouse_id: uuid.UUID
    ) -> list[DailyInventorySnapshot]:
        """Return all snapshots for ``warehouse_id`` across dates/products."""
        return list(
            self._session.scalars(
                select(DailyInventorySnapshot).where(
                    DailyInventorySnapshot.warehouse_id == warehouse_id
                )
            ).all()
        )
