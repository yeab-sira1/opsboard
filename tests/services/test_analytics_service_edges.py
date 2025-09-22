"""Edge-case and aggregation tests for :class:`AnalyticsService`."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
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
def analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(session)


def test_summaries_on_empty_system(analytics: AnalyticsService) -> None:
    assert analytics.get_inventory_summary() == []
    assert analytics.get_order_summary() == {
        status: 0 for status in OrderStatus
    }
    assert analytics.get_reservation_summary() == {
        status: 0 for status in ReservationStatus
    }


def test_inventory_summary_multiple_products_and_warehouses(
    inventory: InventoryService,
    reservations: ReservationService,
    analytics: AnalyticsService,
) -> None:
    p1 = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    p2 = inventory.add_product(sku="SKU-2", name="Gadget", unit="pcs")
    w1 = inventory.create_warehouse(code="WH-1", name="Main", location="B")
    w2 = inventory.create_warehouse(code="WH-2", name="Annex", location="M")

    inventory.set_stock(p1.id, w1.id, 10)
    inventory.set_stock(p1.id, w2.id, 5)
    inventory.set_stock(p2.id, w1.id, 8)
    reservations.create_reservation(p1.id, w1.id, 4, "A")
    reservations.create_reservation(p2.id, w1.id, 3, "B")

    rows = {
        (row.product_id, row.warehouse_id): row
        for row in analytics.get_inventory_summary()
    }
    assert len(rows) == 3
    assert rows[(p1.id, w1.id)].available_stock == 6
    assert rows[(p1.id, w2.id)].available_stock == 5
    assert rows[(p2.id, w1.id)].reserved_quantity == 3
    assert rows[(p2.id, w1.id)].available_stock == 5


def test_order_summary_reflects_completed_and_cancelled(
    inventory: InventoryService,
    reservations: ReservationService,
    orders: OrderService,
    analytics: AnalyticsService,
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    r1 = reservations.create_reservation(product.id, warehouse.id, 2, "A")
    r2 = reservations.create_reservation(product.id, warehouse.id, 2, "B")
    r3 = reservations.create_reservation(product.id, warehouse.id, 2, "C")

    completed = orders.create_order("A", [OrderLine(r1.id, 2)])
    orders.confirm_order(completed.id)
    orders.complete_order(completed.id)

    cancelled = orders.create_order("B", [OrderLine(r2.id, 2)])
    orders.cancel_order(cancelled.id)

    orders.create_order("C", [OrderLine(r3.id, 2)])  # stays PENDING

    summary = analytics.get_order_summary()
    assert summary[OrderStatus.COMPLETED] == 1
    assert summary[OrderStatus.CANCELLED] == 1
    assert summary[OrderStatus.PENDING] == 1
    assert summary[OrderStatus.CONFIRMED] == 0


def test_snapshot_is_point_in_time(
    inventory: InventoryService,
    reservations: ReservationService,
    analytics: AnalyticsService,
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservation = reservations.create_reservation(
        product.id, warehouse.id, 4, "A"
    )

    analytics.generate_daily_snapshot(date(2026, 1, 1))
    day1 = analytics.get_snapshot(date(2026, 1, 1), product.id, warehouse.id)
    assert day1.available_stock == 6

    # Releasing changes live availability but must not alter the stored snapshot.
    reservations.release_reservation(reservation.id)
    analytics.generate_daily_snapshot(date(2026, 1, 2))

    day1_again = analytics.get_snapshot(
        date(2026, 1, 1), product.id, warehouse.id
    )
    day2 = analytics.get_snapshot(date(2026, 1, 2), product.id, warehouse.id)
    assert day1_again.available_stock == 6
    assert day2.available_stock == 10
