"""Integration tests for ReportBundle persistence and order domain events."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from src.models.domain_event import DomainEventType
from src.repositories import ReportBundleRepository
from src.schemas.batch_report_request import BatchReportRequest
from src.services.analytics_service import AnalyticsService
from src.services.batch_report_service import BatchReportService
from src.services.dashboard_service import DashboardService
from src.services.event_service import EventService
from src.services.inventory_service import InventoryService
from src.services.order_service import OrderService
from src.services.reservation_service import ReservationService
from src.value_objects.report_bundle_item import ReportBundleItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_batch_service(session: Session) -> BatchReportService:
    """Build a BatchReportService wired to the given session."""
    dashboard = DashboardService(session)
    analytics = AnalyticsService(session)
    return BatchReportService(dashboard, analytics, session=session)


def _minimal_request() -> BatchReportRequest:
    """Return a non-empty batch request with a single 'orders' item."""
    return BatchReportRequest(items=[ReportBundleItem("orders")])


def _stocked_order(
    session: Session,
) -> tuple[InventoryService, ReservationService, OrderService, object]:
    """Create a product/warehouse with stock and return a PENDING order."""
    from src.services.order_service import OrderLine

    inventory = InventoryService(session)
    reservations = ReservationService(session)
    orders = OrderService(session)

    product = inventory.add_product(sku="SKU-T1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-T1", name="Test Warehouse", location="TestCity"
    )
    inventory.set_stock(product.id, warehouse.id, 10)

    reservation = reservations.create_reservation(
        product.id, warehouse.id, 3, "REF-001"
    )
    order = orders.create_order("REF-001", [OrderLine(reservation.id, 3)])
    return inventory, reservations, orders, order


# ---------------------------------------------------------------------------
# ReportBundle persistence tests
# ---------------------------------------------------------------------------


def test_batch_report_creates_bundle_when_named(session: Session) -> None:
    """generate_batch_reports with bundle_name persists a ReportBundle row."""
    svc = _make_batch_service(session)
    svc.generate_batch_reports(_minimal_request(), bundle_name="daily-run")

    repo = ReportBundleRepository(session)
    bundles = repo.list()
    assert len(bundles) == 1
    assert bundles[0].bundle_name == "daily-run"


def test_batch_report_no_bundle_when_unnamed(session: Session) -> None:
    """generate_batch_reports without bundle_name creates no ReportBundle row."""
    svc = _make_batch_service(session)
    svc.generate_batch_reports(_minimal_request())

    repo = ReportBundleRepository(session)
    assert repo.list() == []


def test_bundle_name_retrievable_via_repository(session: Session) -> None:
    """After creating a named bundle, get_by_name returns the correct record."""
    svc = _make_batch_service(session)
    svc.generate_batch_reports(_minimal_request(), bundle_name="daily-run")

    repo = ReportBundleRepository(session)
    bundle = repo.get_by_name("daily-run")
    assert bundle is not None
    assert bundle.bundle_name == "daily-run"


# ---------------------------------------------------------------------------
# Order domain event tests
# ---------------------------------------------------------------------------


def test_order_completed_emits_domain_event(session: Session) -> None:
    """Completing an order emits an ORDER_COMPLETED domain event."""
    _, _, orders, order = _stocked_order(session)
    orders.confirm_order(order.id)
    orders.complete_order(order.id)

    event_service = EventService(session)
    events = event_service.get_events_by_type(DomainEventType.ORDER_COMPLETED)
    assert len(events) == 1


def test_order_cancelled_emits_domain_event(session: Session) -> None:
    """Cancelling an order emits an ORDER_CANCELLED domain event."""
    _, _, orders, order = _stocked_order(session)
    orders.cancel_order(order.id)

    event_service = EventService(session)
    events = event_service.get_events_by_type(DomainEventType.ORDER_CANCELLED)
    assert len(events) == 1


def test_event_payload_contains_order_reference(session: Session) -> None:
    """The domain event payload includes the order's reference string."""
    _, _, orders, order = _stocked_order(session)
    orders.confirm_order(order.id)
    orders.complete_order(order.id)

    event_service = EventService(session)
    events = event_service.get_events_by_type(DomainEventType.ORDER_COMPLETED)
    assert len(events) == 1

    payload = json.loads(events[0].payload_json)
    assert payload.get("reference") == "REF-001"
    assert "order_id" in payload
