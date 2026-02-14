"""Tests for order/reservation search filtering with populated data."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.schemas import FilterRequest
from src.search.search_service import SearchService
from src.services import (
    AnalyticsService,
    InventoryService,
    OrderLine,
    OrderService,
    ReservationService,
)


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


@pytest.fixture
def orders(session: Session) -> OrderService:
    return OrderService(session)


@pytest.fixture
def search_service(
    orders: OrderService,
    reservations: ReservationService,
    session: Session,
) -> SearchService:
    return SearchService(orders, reservations, AnalyticsService(session))


def _stock(inventory: InventoryService):
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 100)
    return product, warehouse


def test_reservation_text_search_matches_reference(
    inventory: InventoryService,
    reservations: ReservationService,
    search_service: SearchService,
) -> None:
    product, warehouse = _stock(inventory)
    reservations.create_reservation(product.id, warehouse.id, 5, "ALPHA-1")
    reservations.create_reservation(product.id, warehouse.id, 5, "BETA-2")

    result = search_service.search_reservations(
        FilterRequest(search_text="alpha")
    )

    assert result.total_count == 1
    assert result.items[0].reference == "ALPHA-1"


def test_reservation_status_filter(
    inventory: InventoryService,
    reservations: ReservationService,
    search_service: SearchService,
) -> None:
    product, warehouse = _stock(inventory)
    active = reservations.create_reservation(
        product.id, warehouse.id, 5, "A"
    )
    released = reservations.create_reservation(
        product.id, warehouse.id, 5, "B"
    )
    reservations.release_reservation(released.id)

    result = search_service.search_reservations(
        FilterRequest(reservation_statuses=[ReservationStatus.ACTIVE])
    )

    assert result.total_count == 1
    assert result.items[0].id == active.id


def test_order_text_search_matches_reference(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
    search_service: SearchService,
) -> None:
    product, warehouse = _stock(inventory)
    r1 = reservations.create_reservation(product.id, warehouse.id, 5, "r1")
    r2 = reservations.create_reservation(product.id, warehouse.id, 5, "r2")
    orders.create_order("ORDER-ALPHA", [OrderLine(r1.id, 5)])
    orders.create_order("ORDER-BETA", [OrderLine(r2.id, 5)])

    result = search_service.search_orders(
        FilterRequest(search_text="alpha")
    )

    assert result.total_count == 1
    assert result.items[0].reference == "ORDER-ALPHA"


def test_order_status_filter(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
    search_service: SearchService,
) -> None:
    product, warehouse = _stock(inventory)
    r1 = reservations.create_reservation(product.id, warehouse.id, 5, "r1")
    r2 = reservations.create_reservation(product.id, warehouse.id, 5, "r2")
    pending = orders.create_order("ORD-1", [OrderLine(r1.id, 5)])
    confirmed = orders.create_order("ORD-2", [OrderLine(r2.id, 5)])
    orders.confirm_order(confirmed.id)

    result = search_service.search_orders(
        FilterRequest(order_statuses=[OrderStatus.PENDING])
    )

    assert result.total_count == 1
    assert result.items[0].id == pending.id
