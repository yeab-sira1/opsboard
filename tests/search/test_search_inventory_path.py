"""Tests for the non-empty inventory search path of SearchService."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.schemas import FilterRequest
from src.search.search_service import SearchService
from src.services import (
    AnalyticsService,
    InventoryService,
    OrderService,
    ReservationService,
)
from src.value_objects import Pagination, SortSpec


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def search_service(session: Session) -> SearchService:
    return SearchService(
        OrderService(session),
        ReservationService(session),
        AnalyticsService(session),
    )


def _seed_inventory(inventory: InventoryService):
    """Create two products across two warehouses with stock."""
    p1 = inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    p2 = inventory.add_product(sku="SKU-2", name="Gadget", unit="pcs")
    w1 = inventory.create_warehouse(code="WH-1", name="Main", location="B")
    w2 = inventory.create_warehouse(code="WH-2", name="Annex", location="M")
    inventory.set_stock(p1.id, w1.id, 10)
    inventory.set_stock(p1.id, w2.id, 5)
    inventory.set_stock(p2.id, w1.id, 8)
    return p1, p2, w1, w2


def test_inventory_search_returns_all_rows(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _seed_inventory(inventory)
    result = search_service.search_inventory(FilterRequest())

    assert result.total_count == 3
    assert len(result.items) == 3
    assert all("available_stock" in row for row in result.items)


def test_inventory_search_filters_by_product(
    inventory: InventoryService, search_service: SearchService
) -> None:
    p1, _p2, _w1, _w2 = _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(product_ids=[p1.id])
    )

    assert result.total_count == 2
    assert {row["product_id"] for row in result.items} == {p1.id}


def test_inventory_search_filters_by_warehouse(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _p1, _p2, w1, _w2 = _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(warehouse_ids=[w1.id])
    )

    assert result.total_count == 2
    assert {row["warehouse_id"] for row in result.items} == {w1.id}


def test_inventory_search_compound_filter(
    inventory: InventoryService, search_service: SearchService
) -> None:
    p1, _p2, w1, _w2 = _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(product_ids=[p1.id], warehouse_ids=[w1.id])
    )

    assert result.total_count == 1
    row = result.items[0]
    assert row["product_id"] == p1.id
    assert row["warehouse_id"] == w1.id
    assert row["physical_stock"] == 10


def test_inventory_search_sorted_by_available_descending(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(sort_spec=SortSpec("available_stock", ascending=False))
    )

    availables = [row["available_stock"] for row in result.items]
    assert availables == sorted(availables, reverse=True)
    assert availables[0] == 10


def test_inventory_search_sorted_ascending(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(sort_spec=SortSpec("physical_stock", ascending=True))
    )

    physicals = [row["physical_stock"] for row in result.items]
    assert physicals == sorted(physicals)
    assert physicals[0] == 5


def test_inventory_search_pagination(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(
            sort_spec=SortSpec("physical_stock", ascending=True),
            pagination=Pagination(page=1, page_size=2),
        )
    )

    assert result.total_count == 3  # total before pagination
    assert len(result.items) == 2
    assert result.page_size == 2
    assert result.has_next


def test_inventory_search_second_page(
    inventory: InventoryService, search_service: SearchService
) -> None:
    _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(
            sort_spec=SortSpec("physical_stock", ascending=True),
            pagination=Pagination(page=2, page_size=2),
        )
    )

    assert result.total_count == 3
    assert len(result.items) == 1  # remainder on second page
    assert not result.has_next


def test_inventory_search_filter_excluding_all(
    inventory: InventoryService, search_service: SearchService
) -> None:
    import uuid

    _seed_inventory(inventory)
    result = search_service.search_inventory(
        FilterRequest(product_ids=[uuid.uuid4()])
    )

    assert result.total_count == 0
    assert result.items == []
