"""Tests for batch report service."""

import pytest
from sqlalchemy.orm import Session

from src.schemas import BatchReportRequest
from src.services import (
    AnalyticsService,
    DashboardService,
)
from src.services.batch_report_service import BatchReportService
from src.value_objects.report_bundle_item import ReportBundleItem


@pytest.fixture
def dashboard(session: Session) -> DashboardService:
    return DashboardService(session)


@pytest.fixture
def analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(session)


@pytest.fixture
def batch_reports(
    dashboard: DashboardService, analytics: AnalyticsService
) -> BatchReportService:
    return BatchReportService(dashboard, analytics)


def test_empty_request(batch_reports: BatchReportService) -> None:
    req = BatchReportRequest(items=[])
    result = batch_reports.generate_batch_reports(req)
    assert result.total_count == 0
    assert result.generated_count == 0
    assert result.failed_count == 0


def test_single_inventory_report(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("inventory")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 1
    assert result.failed_count == 0
    assert "inventory" in result.results
    assert isinstance(result.results["inventory"], dict)


def test_single_order_report(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("orders")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 1
    assert result.failed_count == 0
    assert "orders" in result.results


def test_single_reservation_report(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("reservations")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 1
    assert result.failed_count == 0
    assert "reservations" in result.results


def test_multiple_reports(
    batch_reports: BatchReportService,
) -> None:
    items = [
        ReportBundleItem("inventory"),
        ReportBundleItem("orders"),
        ReportBundleItem("reservations"),
    ]
    req = BatchReportRequest(items=items)
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 3
    assert result.failed_count == 0
    assert len(result.results) == 3


def test_invalid_report_type(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("invalid_type")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 0
    assert result.failed_count == 1
    assert "invalid_type" in result.results


def test_mixed_success_and_failure(
    batch_reports: BatchReportService,
) -> None:
    items = [
        ReportBundleItem("inventory"),
        ReportBundleItem("unknown"),
        ReportBundleItem("orders"),
    ]
    req = BatchReportRequest(items=items)
    result = batch_reports.generate_batch_reports(req)
    assert result.generated_count == 2
    assert result.failed_count == 1
    assert result.total_count == 3


def test_inventory_report_structure(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("inventory")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    report = result.results["inventory"]
    assert "total_rows" in report
    assert "total_physical" in report
    assert "total_reserved" in report
    assert "total_available" in report


def test_order_report_structure(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("orders")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    report = result.results["orders"]
    assert "total_orders" in report
    assert "counts" in report


def test_reservation_report_structure(
    batch_reports: BatchReportService,
) -> None:
    item = ReportBundleItem("reservations")
    req = BatchReportRequest(items=[item])
    result = batch_reports.generate_batch_reports(req)
    report = result.results["reservations"]
    assert "total_reservations" in report
    assert "counts" in report
