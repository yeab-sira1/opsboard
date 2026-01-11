"""Tests for search service."""

from datetime import date
import uuid

import pytest
from sqlalchemy.orm import Session

from src.models import OrderStatus, ReservationStatus
from src.schemas import FilterRequest
from src.search.search_service import SearchService
from src.services import (
    AnalyticsService,
    OrderService,
    ReservationService,
)
from src.value_objects import DateRange, Pagination, SortSpec


@pytest.fixture
def orders(session: Session) -> OrderService:
    return OrderService(session)


@pytest.fixture
def reservations(session: Session) -> ReservationService:
    return ReservationService(session)


@pytest.fixture
def analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(session)


@pytest.fixture
def search_service(
    orders: OrderService,
    reservations: ReservationService,
    analytics: AnalyticsService,
) -> SearchService:
    return SearchService(orders, reservations, analytics)


def test_search_orders_empty(
    search_service: SearchService,
) -> None:
    req = FilterRequest()
    result = search_service.search_orders(req)
    assert result.items == []
    assert result.total_count == 0
    assert not result.has_next


def test_search_reservations_empty(
    search_service: SearchService,
) -> None:
    req = FilterRequest()
    result = search_service.search_reservations(req)
    assert result.items == []
    assert result.total_count == 0
    assert not result.has_next


def test_search_inventory_empty(
    search_service: SearchService,
) -> None:
    req = FilterRequest()
    result = search_service.search_inventory(req)
    assert result.items == []
    assert result.total_count == 0
    assert not result.has_next


def test_search_with_pagination(
    search_service: SearchService,
) -> None:
    pagination = Pagination(page=1, page_size=10)
    req = FilterRequest(pagination=pagination)
    result = search_service.search_orders(req)
    assert result.page == 1
    assert result.page_size == 10


def test_search_with_sort_spec(
    search_service: SearchService,
) -> None:
    sort = SortSpec("created_at", ascending=False)
    req = FilterRequest(sort_spec=sort)
    result = search_service.search_orders(req)
    assert result.total_count == 0


def test_search_with_date_range_filter(
    search_service: SearchService,
) -> None:
    dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
    req = FilterRequest(date_range=dr)
    result = search_service.search_orders(req)
    assert result.total_count == 0


def test_search_with_status_filter(
    search_service: SearchService,
) -> None:
    req = FilterRequest(order_statuses=[OrderStatus.PENDING])
    result = search_service.search_orders(req)
    assert result.total_count == 0


def test_search_reservations_with_status_filter(
    search_service: SearchService,
) -> None:
    req = FilterRequest(reservation_statuses=[ReservationStatus.ACTIVE])
    result = search_service.search_reservations(req)
    assert result.total_count == 0


def test_search_inventory_with_search_text(
    search_service: SearchService,
) -> None:
    req = FilterRequest(search_text="widget")
    result = search_service.search_inventory(req)
    assert result.total_count == 0


def test_pagination_default(
    search_service: SearchService,
) -> None:
    req = FilterRequest()
    result = search_service.search_orders(req)
    assert result.page == 1
    assert result.page_size == 20


def test_pagination_has_next_calculation(
    search_service: SearchService,
) -> None:
    pagination = Pagination(page=1, page_size=10)
    req = FilterRequest(pagination=pagination)
    result = search_service.search_orders(req)
    assert not result.has_next
