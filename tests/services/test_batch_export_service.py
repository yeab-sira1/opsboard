"""Tests for batch export service."""

import pytest
from sqlalchemy.orm import Session

from src.schemas import BatchReportRequest
from src.services import ExportService
from src.services.batch_export_service import BatchExportService
from src.value_objects.report_bundle_item import ReportBundleItem


@pytest.fixture
def export_svc(session: Session) -> ExportService:
    return ExportService(session)


@pytest.fixture
def batch_export(export_svc: ExportService) -> BatchExportService:
    return BatchExportService(export_svc)


def test_empty_export_request(batch_export: BatchExportService) -> None:
    req = BatchReportRequest(items=[])
    result = batch_export.export_batch_csv(req)
    assert result == {}


def test_single_inventory_export(batch_export: BatchExportService) -> None:
    item = ReportBundleItem("inventory")
    req = BatchReportRequest(items=[item])
    result = batch_export.export_batch_csv(req)
    assert "inventory" in result
    assert isinstance(result["inventory"], str)


def test_single_order_export(batch_export: BatchExportService) -> None:
    item = ReportBundleItem("orders")
    req = BatchReportRequest(items=[item])
    result = batch_export.export_batch_csv(req)
    assert "orders" in result
    assert isinstance(result["orders"], str)


def test_single_reservation_export(batch_export: BatchExportService) -> None:
    item = ReportBundleItem("reservations")
    req = BatchReportRequest(items=[item])
    result = batch_export.export_batch_csv(req)
    assert "reservations" in result
    assert isinstance(result["reservations"], str)


def test_multiple_exports(batch_export: BatchExportService) -> None:
    items = [
        ReportBundleItem("inventory"),
        ReportBundleItem("orders"),
        ReportBundleItem("reservations"),
    ]
    req = BatchReportRequest(items=items)
    result = batch_export.export_batch_csv(req)
    assert len(result) == 3
    assert all(isinstance(v, str) for v in result.values())


def test_invalid_report_type_export(batch_export: BatchExportService) -> None:
    item = ReportBundleItem("unknown")
    req = BatchReportRequest(items=[item])
    result = batch_export.export_batch_csv(req)
    assert "unknown" in result
    assert "Error" in result["unknown"]


def test_mixed_success_and_failure_export(
    batch_export: BatchExportService,
) -> None:
    items = [
        ReportBundleItem("inventory"),
        ReportBundleItem("invalid"),
        ReportBundleItem("orders"),
    ]
    req = BatchReportRequest(items=items)
    result = batch_export.export_batch_csv(req)
    assert len(result) == 3
    assert "Error" in result["invalid"]
    assert "Error" not in result["inventory"]
    assert "Error" not in result["orders"]
