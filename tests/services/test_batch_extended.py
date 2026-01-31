"""Extended batch reporting and bundle tests."""

import pytest
from sqlalchemy.orm import Session

from src.models import ReportBundle
from src.repositories.report_bundle_repository import ReportBundleRepository
from src.schemas import BatchReportRequest, BatchReportResult
from src.services.batch_report_service import BatchReportService
from src.services import AnalyticsService, DashboardService, ExportService
from src.services.batch_export_service import BatchExportService
from src.value_objects.report_bundle_item import ReportBundleItem


@pytest.fixture
def batch_report(
    session: Session,
) -> BatchReportService:
    dashboard = DashboardService(session)
    analytics = AnalyticsService(session)
    return BatchReportService(dashboard, analytics)


@pytest.fixture
def batch_export(session: Session) -> BatchExportService:
    export = ExportService(session)
    return BatchExportService(export)


class TestBatchReportingEdgeCases:
    def test_empty_batch_is_consistent(
        self, batch_report: BatchReportService
    ) -> None:
        req1 = BatchReportRequest(items=[])
        req2 = BatchReportRequest(items=[])
        result1 = batch_report.generate_batch_reports(req1)
        result2 = batch_report.generate_batch_reports(req2)
        assert result1.generated_count == result2.generated_count
        assert result1.failed_count == result2.failed_count

    def test_duplicate_report_types(
        self, batch_report: BatchReportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("inventory"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert result.generated_count == 2
        assert len(result.results) == 1
        assert "inventory" in result.results

    def test_all_report_types_combined(
        self, batch_report: BatchReportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("orders"),
            ReportBundleItem("reservations"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert result.all_succeeded
        assert result.total_count == 3

    def test_batch_continues_on_error(
        self, batch_report: BatchReportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("unknown1"),
            ReportBundleItem("orders"),
            ReportBundleItem("unknown2"),
            ReportBundleItem("reservations"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert result.generated_count == 3
        assert result.failed_count == 2
        assert result.total_count == 5

    def test_result_counts_match_items(
        self, batch_report: BatchReportService
    ) -> None:
        items = [ReportBundleItem(f"type_{i}") for i in range(10)]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert result.total_count == 10
        assert result.generated_count + result.failed_count == 10

    def test_error_details_captured(
        self, batch_report: BatchReportService
    ) -> None:
        items = [ReportBundleItem("invalid_type")]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert "error" in result.results["invalid_type"]
        assert isinstance(result.results["invalid_type"]["error"], str)


class TestBatchExportingEdgeCases:
    def test_empty_export_is_consistent(
        self, batch_export: BatchExportService
    ) -> None:
        req1 = BatchReportRequest(items=[])
        req2 = BatchReportRequest(items=[])
        result1 = batch_export.export_batch_csv(req1)
        result2 = batch_export.export_batch_csv(req2)
        assert len(result1) == len(result2)

    def test_duplicate_export_types(
        self, batch_export: BatchExportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("inventory"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_export.export_batch_csv(req)
        assert len(result) == 1
        assert "inventory" in result

    def test_all_export_types_combined(
        self, batch_export: BatchExportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("orders"),
            ReportBundleItem("reservations"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_export.export_batch_csv(req)
        assert len(result) == 3
        assert all(isinstance(v, str) for v in result.values())

    def test_csv_export_continues_on_error(
        self, batch_export: BatchExportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("unknown"),
            ReportBundleItem("orders"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_export.export_batch_csv(req)
        assert len(result) == 3
        assert "Error" in result["unknown"]


class TestBundleIntegration:
    def test_bundle_persistence(
        self, session: Session
    ) -> None:
        repo = ReportBundleRepository(session)
        bundle = ReportBundle(bundle_name="Integration Test")
        repo.add(bundle)
        retrieved = repo.get(bundle.id)
        assert retrieved is not None
        assert retrieved.bundle_name == "Integration Test"

    def test_multiple_bundles(
        self, session: Session
    ) -> None:
        repo = ReportBundleRepository(session)
        bundles = [
            ReportBundle(bundle_name=f"Bundle {i}") for i in range(5)
        ]
        for b in bundles:
            repo.add(b)
        all_bundles = repo.list()
        assert len(all_bundles) == 5

    def test_bundle_with_batch_request(
        self, batch_report: BatchReportService
    ) -> None:
        items = [
            ReportBundleItem("inventory"),
            ReportBundleItem("orders"),
        ]
        req = BatchReportRequest(items=items)
        result = batch_report.generate_batch_reports(req)
        assert result.generated_count == 2


class TestBatchResultProperties:
    def test_all_succeeded_true_when_no_failures(self) -> None:
        result = BatchReportResult(
            results={"r1": {}, "r2": {}},
            generated_count=2,
            failed_count=0,
        )
        assert result.all_succeeded

    def test_all_succeeded_false_when_any_failure(self) -> None:
        result = BatchReportResult(
            results={"r1": {}, "r2": {}},
            generated_count=1,
            failed_count=1,
        )
        assert not result.all_succeeded

    def test_total_count_accurate(self) -> None:
        result = BatchReportResult(
            results={},
            generated_count=7,
            failed_count=3,
        )
        assert result.total_count == 10
