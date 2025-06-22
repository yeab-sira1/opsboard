"""Repository for :class:`StockRecord` persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.stock_record import StockRecord
from src.repositories.base_repository import BaseRepository


class StockRecordRepository(BaseRepository[StockRecord]):
    """CRUD operations and lookups for stock records."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, StockRecord)

    def get_by_product_and_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> StockRecord | None:
        """Return the stock record for a (product, warehouse) pair, if any."""
        return self._session.scalar(
            select(StockRecord).where(
                StockRecord.product_id == product_id,
                StockRecord.warehouse_id == warehouse_id,
            )
        )
