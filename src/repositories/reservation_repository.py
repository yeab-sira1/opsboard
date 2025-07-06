"""Repository for :class:`Reservation` persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.reservation import Reservation, ReservationStatus
from src.repositories.base_repository import BaseRepository


class ReservationRepository(BaseRepository[Reservation]):
    """CRUD operations and lookups for reservations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Reservation)

    def get_active_by_product_and_warehouse(
        self, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> list[Reservation]:
        """Return active reservations for a (product, warehouse) pair."""
        return list(
            self._session.scalars(
                select(Reservation).where(
                    Reservation.product_id == product_id,
                    Reservation.warehouse_id == warehouse_id,
                    Reservation.status == ReservationStatus.ACTIVE,
                )
            ).all()
        )

    def get_by_reference(self, reference: str) -> list[Reservation]:
        """Return all reservations sharing ``reference``."""
        return list(
            self._session.scalars(
                select(Reservation).where(Reservation.reference == reference)
            ).all()
        )

    def get_active_by_reference(self, reference: str) -> list[Reservation]:
        """Return active reservations sharing ``reference``."""
        return list(
            self._session.scalars(
                select(Reservation).where(
                    Reservation.reference == reference,
                    Reservation.status == ReservationStatus.ACTIVE,
                )
            ).all()
        )
