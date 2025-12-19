"""Tests for :class:`CacheService` and reporting integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from src.services import (
    CacheSerializationError,
    CacheService,
    DashboardService,
    ExportService,
    InventoryService,
    ReservationService,
)


class FakeClock:
    """A controllable clock for deterministic expiry tests."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_set_get_delete(session: Session) -> None:
    cache = CacheService(session)
    cache.set("k", {"a": 1})

    assert cache.get("k") == {"a": 1}
    assert cache.exists("k") is True
    assert cache.delete("k") is True
    assert cache.get("k") is None
    assert cache.exists("k") is False


def test_missing_key_returns_none(session: Session) -> None:
    cache = CacheService(session)
    assert cache.get("missing") is None
    assert cache.delete("missing") is False


def test_overwrite_key(session: Session) -> None:
    cache = CacheService(session)
    cache.set("k", 1)
    cache.set("k", 2)
    assert cache.get("k") == 2


def test_expired_entry_behaves_as_missing(
    session: Session, clock: FakeClock
) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", "v", ttl_seconds=10)

    assert cache.get("k") == "v"
    clock.advance(11)
    assert cache.get("k") is None
    assert cache.exists("k") is False


def test_clear_expired(session: Session, clock: FakeClock) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("short", 1, ttl_seconds=10)
    cache.set("long", 2, ttl_seconds=100)
    cache.set("forever", 3)

    clock.advance(50)
    removed = cache.clear_expired()
    assert removed == 1
    assert cache.get("short") is None
    assert cache.get("long") == 2
    assert cache.get("forever") == 3


def test_non_serializable_value_raises(session: Session) -> None:
    cache = CacheService(session)
    with pytest.raises(CacheSerializationError):
        cache.set("k", object())


def test_get_or_set_invokes_producer_once(session: Session) -> None:
    cache = CacheService(session)
    calls = {"n": 0}

    def producer() -> int:
        calls["n"] += 1
        return 42

    assert cache.get_or_set("k", producer) == 42
    assert cache.get_or_set("k", producer) == 42
    assert calls["n"] == 1


# --- Reporting integration ----------------------------------------------


def _seed(
    inventory: InventoryService, reservations: ReservationService
) -> None:
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)
    reservations.create_reservation(product.id, warehouse.id, 4, "A")


def test_export_service_caches_csv(session: Session) -> None:
    inventory = InventoryService(session)
    reservations = ReservationService(session)
    _seed(inventory, reservations)

    cache = CacheService(session)
    export = ExportService(session, cache=cache)

    first = export.export_order_summary_csv()
    assert cache.exists("export:order_summary")
    second = export.export_order_summary_csv()
    assert first == second


def test_dashboard_service_caches_counts(session: Session) -> None:
    inventory = InventoryService(session)
    reservations = ReservationService(session)
    _seed(inventory, reservations)

    cache = CacheService(session)
    dashboard = DashboardService(session, cache=cache)

    view = dashboard.get_reservation_dashboard()
    assert view.total_reservations == 1
    assert cache.exists("dashboard:reservation_counts")


def test_services_without_cache_still_work(session: Session) -> None:
    inventory = InventoryService(session)
    reservations = ReservationService(session)
    _seed(inventory, reservations)

    export = ExportService(session)
    dashboard = DashboardService(session)
    assert export.export_order_summary_csv().startswith("status,count")
    assert dashboard.get_order_dashboard().total_orders == 0
