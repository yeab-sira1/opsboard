"""Extended search and pagination tests."""

from datetime import date
import uuid

import pytest

from src.schemas import FilterResult
from src.value_objects import Pagination


class TestFilterResultPagination:
    def test_first_page_with_more_pages(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20)), total_count=50, page=1, page_size=20
        )
        assert result.has_next
        assert not result.has_next is False

    def test_middle_page_with_pages_before_and_after(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20, 40)), total_count=100, page=2, page_size=20
        )
        assert result.has_next
        assert result.page == 2

    def test_last_page_exact(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(80, 100)), total_count=100, page=5, page_size=20
        )
        assert not result.has_next
        assert result.page == 5

    def test_last_page_with_fewer_items(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=[90, 91, 92, 93, 94], total_count=94, page=5, page_size=20
        )
        assert not result.has_next

    def test_one_page_only(self) -> None:
        result: FilterResult[str] = FilterResult(
            items=["a", "b", "c"], total_count=3, page=1, page_size=20
        )
        assert not result.has_next

    def test_exactly_one_full_page_boundary(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20)), total_count=20, page=1, page_size=20
        )
        assert not result.has_next

    def test_large_page_size_single_page(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(1000)),
            total_count=1000,
            page=1,
            page_size=5000,
        )
        assert not result.has_next

    def test_page_3_of_10(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(40, 60)), total_count=200, page=3, page_size=20
        )
        assert result.has_next
        assert result.page == 3
        assert result.page_size == 20

    def test_page_10_of_10(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(180, 200)), total_count=200, page=10, page_size=20
        )
        assert not result.has_next

    def test_single_item_single_page(self) -> None:
        result: FilterResult[str] = FilterResult(
            items=["only"], total_count=1, page=1, page_size=20
        )
        assert not result.has_next

    def test_rounding_up_last_page(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=[85, 86, 87, 88, 89],
            total_count=89,
            page=5,
            page_size=20,
        )
        assert not result.has_next

    def test_off_by_one_boundary(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20, 40)), total_count=41, page=2, page_size=20
        )
        assert result.has_next


class TestPaginationCalculations:
    def test_offset_page_1_size_10(self) -> None:
        p = Pagination(page=1, page_size=10)
        assert p.offset == 0

    def test_offset_page_2_size_10(self) -> None:
        p = Pagination(page=2, page_size=10)
        assert p.offset == 10

    def test_offset_page_5_size_25(self) -> None:
        p = Pagination(page=5, page_size=25)
        assert p.offset == 100

    def test_offset_page_10_size_50(self) -> None:
        p = Pagination(page=10, page_size=50)
        assert p.offset == 450

    def test_limit_equals_page_size(self) -> None:
        p = Pagination(page=3, page_size=15)
        assert p.limit == 15

    def test_large_page_numbers(self) -> None:
        p = Pagination(page=1000, page_size=100)
        assert p.offset == 99900
        assert p.limit == 100

    def test_page_size_1(self) -> None:
        p = Pagination(page=5, page_size=1)
        assert p.offset == 4
        assert p.limit == 1

    def test_page_size_1000(self) -> None:
        p = Pagination(page=2, page_size=1000)
        assert p.offset == 1000
        assert p.limit == 1000


class TestCompoundFilters:
    def test_multiple_filter_types_combined(self) -> None:
        from src.search.filter_spec import FilterSpec
        from src.models import OrderStatus, ReservationStatus
        from src.value_objects import DateRange

        product_ids = [uuid.uuid4(), uuid.uuid4()]
        warehouse_ids = [uuid.uuid4()]
        order_statuses = [OrderStatus.COMPLETED, OrderStatus.PENDING]
        date_range = DateRange(date(2025, 1, 1), date(2025, 12, 31))

        spec = FilterSpec(
            product_ids=product_ids,
            warehouse_ids=warehouse_ids,
            order_statuses=order_statuses,
            date_range=date_range,
            search_text="urgent",
        )

        assert spec.matches_product(product_ids[0])
        assert spec.matches_product(product_ids[1])
        assert not spec.matches_product(uuid.uuid4())
        assert spec.matches_warehouse(warehouse_ids[0])
        assert not spec.matches_warehouse(uuid.uuid4())
        assert spec.matches_order_status(OrderStatus.COMPLETED)
        assert spec.matches_order_status(OrderStatus.PENDING)
        assert not spec.matches_order_status(OrderStatus.CANCELLED)
        assert spec.matches_date(date(2025, 6, 15))
        assert not spec.matches_date(date(2024, 12, 31))
        assert spec.matches_text("URGENT DELIVERY")
        assert not spec.matches_text("standard")

    def test_empty_filter_matches_nothing_restricted(self) -> None:
        from src.search.filter_spec import FilterSpec

        spec = FilterSpec()
        assert spec.matches_product(uuid.uuid4())
        assert spec.matches_warehouse(uuid.uuid4())
        assert spec.matches_date(date.today())
        assert spec.matches_text("anything at all")


class TestEdgeCases:
    def test_filter_result_zero_total_count(self) -> None:
        result: FilterResult[int] = FilterResult(
            items=[], total_count=0, page=1, page_size=20
        )
        assert result.total_count == 0
        assert len(result.items) == 0
        assert not result.has_next

    def test_filter_result_items_fewer_than_page_size(self) -> None:
        result: FilterResult[str] = FilterResult(
            items=["a", "b", "c"],
            total_count=3,
            page=1,
            page_size=20,
        )
        assert len(result.items) == 3
        assert not result.has_next

    def test_filter_result_total_count_larger_than_returned_items(
        self,
    ) -> None:
        result: FilterResult[int] = FilterResult(
            items=list(range(20)), total_count=100, page=1, page_size=20
        )
        assert len(result.items) == 20
        assert result.total_count == 100
        assert result.has_next

    def test_pagination_consistency(self) -> None:
        p1 = Pagination(page=1, page_size=10)
        p2 = Pagination(page=1, page_size=10)
        assert p1 == p2
        assert p1.offset == p2.offset
        assert p1.limit == p2.limit

    def test_date_range_boundary_dates(self) -> None:
        from src.value_objects import DateRange

        start = date(2025, 1, 1)
        end = date(2025, 1, 1)
        dr = DateRange(start, end)
        assert dr.contains(start)
        assert dr.contains(end)
        assert not dr.contains(date(2024, 12, 31))
        assert not dr.contains(date(2025, 1, 2))
