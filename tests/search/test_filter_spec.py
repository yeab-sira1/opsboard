"""Tests for filter specifications."""

from datetime import date
import uuid

import pytest

from src.models import OrderStatus, ReservationStatus
from src.search.filter_spec import FilterSpec
from src.search.query_filter import QueryFilter
from src.value_objects import DateRange, SortSpec


class TestFilterSpec:
    def test_empty_spec_matches_all(self) -> None:
        spec = FilterSpec()
        assert spec.matches_product(uuid.uuid4())
        assert spec.matches_warehouse(uuid.uuid4())
        assert spec.matches_order_status(OrderStatus.PENDING)
        assert spec.matches_reservation_status(ReservationStatus.ACTIVE)
        assert spec.matches_report_type("daily")
        assert spec.matches_date(date(2025, 6, 15))
        assert spec.matches_text("anything")

    def test_product_filter(self) -> None:
        product_id = uuid.uuid4()
        other_id = uuid.uuid4()
        spec = FilterSpec(product_ids=[product_id])
        assert spec.matches_product(product_id)
        assert not spec.matches_product(other_id)

    def test_multiple_product_ids(self) -> None:
        id1, id2, id3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        spec = FilterSpec(product_ids=[id1, id2])
        assert spec.matches_product(id1)
        assert spec.matches_product(id2)
        assert not spec.matches_product(id3)

    def test_warehouse_filter(self) -> None:
        wh_id = uuid.uuid4()
        other_id = uuid.uuid4()
        spec = FilterSpec(warehouse_ids=[wh_id])
        assert spec.matches_warehouse(wh_id)
        assert not spec.matches_warehouse(other_id)

    def test_order_status_filter(self) -> None:
        spec = FilterSpec(order_statuses=[OrderStatus.COMPLETED])
        assert spec.matches_order_status(OrderStatus.COMPLETED)
        assert not spec.matches_order_status(OrderStatus.PENDING)

    def test_multiple_order_statuses(self) -> None:
        spec = FilterSpec(
            order_statuses=[OrderStatus.COMPLETED, OrderStatus.PENDING]
        )
        assert spec.matches_order_status(OrderStatus.COMPLETED)
        assert spec.matches_order_status(OrderStatus.PENDING)
        assert not spec.matches_order_status(OrderStatus.CANCELLED)

    def test_reservation_status_filter(self) -> None:
        spec = FilterSpec(reservation_statuses=[ReservationStatus.ACTIVE])
        assert spec.matches_reservation_status(ReservationStatus.ACTIVE)
        assert not spec.matches_reservation_status(ReservationStatus.FULFILLED)

    def test_report_type_filter(self) -> None:
        spec = FilterSpec(report_types=["daily", "weekly"])
        assert spec.matches_report_type("daily")
        assert spec.matches_report_type("weekly")
        assert not spec.matches_report_type("monthly")

    def test_date_range_filter(self) -> None:
        dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        spec = FilterSpec(date_range=dr)
        assert spec.matches_date(date(2025, 6, 15))
        assert spec.matches_date(date(2025, 1, 1))
        assert spec.matches_date(date(2025, 12, 31))
        assert not spec.matches_date(date(2024, 12, 31))
        assert not spec.matches_date(date(2026, 1, 1))

    def test_text_filter_case_insensitive(self) -> None:
        spec = FilterSpec(search_text="widget")
        assert spec.matches_text("widget")
        assert spec.matches_text("WIDGET")
        assert spec.matches_text("I have a Widget")
        assert not spec.matches_text("gadget")

    def test_text_filter_partial_match(self) -> None:
        spec = FilterSpec(search_text="ing")
        assert spec.matches_text("processing")
        assert spec.matches_text("pending orders")
        assert not spec.matches_text("happy")

    def test_compound_filters(self) -> None:
        product_id = uuid.uuid4()
        wh_id = uuid.uuid4()
        dr = DateRange(date(2025, 1, 1), date(2025, 12, 31))
        spec = FilterSpec(
            product_ids=[product_id],
            warehouse_ids=[wh_id],
            order_statuses=[OrderStatus.COMPLETED],
            date_range=dr,
            search_text="urgent",
        )
        assert spec.matches_product(product_id)
        assert spec.matches_warehouse(wh_id)
        assert spec.matches_order_status(OrderStatus.COMPLETED)
        assert spec.matches_date(date(2025, 6, 15))
        assert spec.matches_text("URGENT TASK")
        assert not spec.matches_order_status(OrderStatus.PENDING)


class TestQueryFilter:
    def test_filter_with_predicate(self) -> None:
        items = [1, 2, 3, 4, 5]
        spec = FilterSpec()
        result = QueryFilter.apply_filter(
            items, spec, lambda x: x > 2
        )
        assert result == [3, 4, 5]

    def test_sort_ascending(self) -> None:
        items = [3, 1, 4, 1, 5]
        sort_spec = SortSpec("value", ascending=True)
        result = QueryFilter.apply_sort(
            items, sort_spec, lambda x: x
        )
        assert result == [1, 1, 3, 4, 5]

    def test_sort_descending(self) -> None:
        items = [3, 1, 4, 1, 5]
        sort_spec = SortSpec("value", ascending=False)
        result = QueryFilter.apply_sort(
            items, sort_spec, lambda x: x
        )
        assert result == [5, 4, 3, 1, 1]

    def test_sort_none_returns_unchanged(self) -> None:
        items = [3, 1, 4]
        result = QueryFilter.apply_sort(
            items, None, lambda x: x
        )
        assert result == [3, 1, 4]

    def test_pagination_first_page(self) -> None:
        items = list(range(100))
        result = QueryFilter.apply_pagination(items, offset=0, limit=20)
        assert result == list(range(20))

    def test_pagination_middle_page(self) -> None:
        items = list(range(100))
        result = QueryFilter.apply_pagination(items, offset=40, limit=20)
        assert result == list(range(40, 60))

    def test_pagination_last_page(self) -> None:
        items = list(range(100))
        result = QueryFilter.apply_pagination(items, offset=80, limit=20)
        assert result == list(range(80, 100))

    def test_pagination_partial_last_page(self) -> None:
        items = list(range(95))
        result = QueryFilter.apply_pagination(items, offset=80, limit=20)
        assert result == list(range(80, 95))

    def test_pagination_empty_result(self) -> None:
        items: list[int] = []
        result = QueryFilter.apply_pagination(items, offset=0, limit=20)
        assert result == []
