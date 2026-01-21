"""Tests for batch report schemas."""

import pytest

from src.schemas import BatchReportRequest, BatchReportResult
from src.value_objects.report_bundle_item import ReportBundleItem


class TestBatchReportRequest:
    def test_empty_request(self) -> None:
        req = BatchReportRequest(items=[])
        assert req.is_empty()
        assert len(req.items) == 0

    def test_single_item_request(self) -> None:
        item = ReportBundleItem("inventory")
        req = BatchReportRequest(items=[item])
        assert not req.is_empty()
        assert len(req.items) == 1
        assert req.items[0] == item

    def test_multiple_items_request(self) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("orders", '{"status": "completed"}'),
            ReportBundleItem("reservations"),
        ]
        req = BatchReportRequest(items=items)
        assert not req.is_empty()
        assert len(req.items) == 3

    def test_multiple_same_type_items(self) -> None:
        items = [
            ReportBundleItem("daily", '{"type": "inventory"}'),
            ReportBundleItem("daily", '{"type": "orders"}'),
        ]
        req = BatchReportRequest(items=items)
        assert len(req.items) == 2


class TestBatchReportResult:
    def test_all_succeeded(self) -> None:
        result = BatchReportResult(
            results={"report1": {"status": "ok"}},
            generated_count=1,
            failed_count=0,
        )
        assert result.total_count == 1
        assert result.all_succeeded

    def test_some_failures(self) -> None:
        result = BatchReportResult(
            results={
                "report1": {"status": "ok"},
                "report2": {"error": "failed"},
            },
            generated_count=1,
            failed_count=1,
        )
        assert result.total_count == 2
        assert not result.all_succeeded

    def test_all_failed(self) -> None:
        result = BatchReportResult(
            results={},
            generated_count=0,
            failed_count=3,
        )
        assert result.total_count == 3
        assert not result.all_succeeded

    def test_empty_result(self) -> None:
        result = BatchReportResult(
            results={},
            generated_count=0,
            failed_count=0,
        )
        assert result.total_count == 0
        assert result.all_succeeded

    def test_total_count_calculation(self) -> None:
        result = BatchReportResult(
            results={"r1": {}, "r2": {}, "r3": {}},
            generated_count=5,
            failed_count=3,
        )
        assert result.total_count == 8
