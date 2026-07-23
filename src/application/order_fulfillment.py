"""Order-fulfillment use-case orchestrator.

Coordinates :class:`~src.services.ReservationService` and
:class:`~src.services.OrderService` for the common reservation → order →
confirm → complete / cancel lifecycle.  Business rules live exclusively in
the service layer; this class only sequences the calls.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import NamedTuple

from src.container import Container
from src.models.order import Order
from src.models.reservation import Reservation
from src.services.order_service import OrderLine


class ReservationRequest(NamedTuple):
    """Input for creating a single reservation."""

    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reference: str


class OrderFulfillmentApp:
    """Orchestrates reservation and order operations.

    All methods delegate entirely to the underlying services; no business
    logic is duplicated here.

    Parameters
    ----------
    container:
        A :class:`~src.container.Container` bound to the current session.
    """

    def __init__(self, container: Container) -> None:
        self._c = container

    def reserve_and_create_order(
        self,
        reference: str,
        reservation_requests: Sequence[ReservationRequest],
    ) -> tuple[list[Reservation], Order]:
        """Reserve stock for each request, then create a single order.

        Returns a ``(reservations, order)`` tuple.  All reservations and the
        order are created in the same database session.

        Parameters
        ----------
        reference:
            Unique order reference string.
        reservation_requests:
            One entry per product/warehouse/quantity combination.
        """
        reservations: list[Reservation] = []
        for req in reservation_requests:
            reservation = self._c.reservations.create_reservation(
                product_id=req.product_id,
                warehouse_id=req.warehouse_id,
                quantity=req.quantity,
                reference=req.reference,
            )
            reservations.append(reservation)

        lines = [
            OrderLine(reservation_id=r.id, quantity=r.quantity)
            for r in reservations
        ]
        order = self._c.orders.create_order(reference=reference, lines=lines)
        return reservations, order

    def confirm_and_complete(self, order_id: uuid.UUID) -> Order:
        """Confirm then immediately complete an order.

        Useful in testing and simple automated flows where no human approval
        step is required.

        Parameters
        ----------
        order_id:
            Primary key of the order to advance.
        """
        self._c.orders.confirm_order(order_id)
        return self._c.orders.complete_order(order_id)

    def cancel(self, order_id: uuid.UUID) -> Order:
        """Cancel an order, releasing its reservations.

        Parameters
        ----------
        order_id:
            Primary key of the order to cancel.
        """
        return self._c.orders.cancel_order(order_id)
