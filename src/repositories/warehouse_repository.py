"""Repository for :class:`Warehouse` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.warehouse import Warehouse
from src.repositories.base_repository import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    """CRUD operations and code lookups for warehouses."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Warehouse)

    def get_by_code(self, code: str) -> Warehouse | None:
        """Return the warehouse with ``code`` or ``None`` if absent."""
        return self._session.scalar(
            select(Warehouse).where(Warehouse.code == code)
        )
