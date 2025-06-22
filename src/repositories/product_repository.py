"""Repository for :class:`Product` persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.product import Product
from src.repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """CRUD operations and SKU lookups for products."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Product)

    def get_by_sku(self, sku: str) -> Product | None:
        """Return the product with ``sku`` or ``None`` if absent."""
        return self._session.scalar(select(Product).where(Product.sku == sku))
