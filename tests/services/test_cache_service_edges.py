"""Edge-case tests for :class:`CacheService` and reporting integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from src.services import (
    CacheService,
    DashboardService,
    ExportService,
    InventoryService,
    ReservationService,
)


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_expiry_boundary_is_inclusive(
    session: Session, clock: FakeClock
) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", "v", ttl_seconds=10)

    clock.advance(10)  # exactly at expiry
    assert cache.get("k") is None


def test_just_before_expiry_is_live(
    session: Session, clock: FakeClock
) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", "v", ttl_seconds=10)

    clock.advance(9)
    assert cache.get("k") == "v"


def test_overwrite_resets_ttl(session: Session, clock: FakeClock) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", "v", ttl_seconds=10)
    clock.advance(8)
    cache.set("k", "v2", ttl_seconds=10)  # fresh 10s from now

    clock.advance(5)  # 13s since first set, 5s since overwrite
    assert cache.get("k") == "v2"


def test_setting_without_ttl_removes_expiry(
    session: Session, clock: FakeClock
) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", "v", ttl_seconds=10)
    cache.set("k", "v2")  # no ttl -> never expires

    clock.advance(1000)
    assert cache.get("k") == "v2"


def test_repeated_reads_are_stable(session: Session) -> None:
    cache = CacheService(session)
    cache.set("k", {"x": [1, 2, 3]})
    assert cache.get("k") == cache.get("k") == {"x": [1, 2, 3]}


def test_complex_payload_round_trip(session: Session) -> None:
    cache = CacheService(session)
    payload = {"a": 1, "b": [1, 2, {"c": True}], "d": None}
    cache.set("k", payload)
    assert cache.get("k") == payload


def test_clear_expired_returns_zero_when_nothing_expired(
    session: Session, clock: FakeClock
) -> None:
    cache = CacheService(session, clock=clock)
    cache.set("k", 1, ttl_seconds=100)
    cache.set("forever", 2)
    assert cache.clear_expired() == 0


def test_cached_export_is_stale_until_cleared(session: Session) -> None:
    # Documents the "cache wraps reads only; no invalidation" contract.
    inventory = InventoryService(session)
    reservations = ReservationService(session)
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)

    cache = CacheService(session)
    export = ExportService(session, cache=cache)

    first = export.export_reservation_summary_csv()
    # A write happens through the normal service after the cache is populated.
    reservations.create_reservation(product.id, warehouse.id, 4, "A")
    cached = export.export_reservation_summary_csv()
    assert cached == first  # still the cached (stale) value

    cache.delete("export:reservation_summary")
    fresh = export.export_reservation_summary_csv()
    assert "ACTIVE,1" in fresh


def test_dashboard_uncached_reflects_writes_immediately(
    session: Session,
) -> None:
    inventory = InventoryService(session)
    reservations = ReservationService(session)
    product = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    warehouse = inventory.create_warehouse(
        code="WH-1", name="Main", location="B"
    )
    inventory.set_stock(product.id, warehouse.id, 10)

    dashboard = DashboardService(session)  # no cache
    assert dashboard.get_reservation_dashboard().total_reservations == 0
    reservations.create_reservation(product.id, warehouse.id, 4, "A")
    assert dashboard.get_reservation_dashboard().total_reservations == 1
