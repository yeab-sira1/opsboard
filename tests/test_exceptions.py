"""Tests for the centralized exception hierarchy."""

from __future__ import annotations

import uuid

from src.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    OpsboardError,
    ValidationError,
)
from src.services.analytics_service import (
    AnalyticsError,
    SnapshotAlreadyExistsError,
    SnapshotNotFoundError,
)
from src.services.cache_service import CacheError, CacheSerializationError
from src.services.import_service import (
    BulkImportError,
    InvalidImportQuantityError,
    MalformedCsvError,
    UnknownProductError,
    UnknownWarehouseError,
)
from src.services.inventory_service import (
    InventoryError,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from src.services.notification_service import (
    InvalidNotificationStateError,
    NotificationError,
    NotificationNotFoundError,
)
from src.services.order_service import (
    DuplicateOrderReferenceError,
    EmptyOrderError,
    InactiveReservationError,
    InvalidOrderStateError,
    OrderError,
    OrderNotFoundError,
    OrderQuantityMismatchError,
)
from src.services.report_job_service import (
    InvalidReportJobStateError,
    ReportJobError,
    ReportJobNotFoundError,
    ReportRequestNotFoundError,
)
from src.services.reservation_service import (
    InsufficientAvailableStockError,
    InvalidReservationQuantityError,
    ReservationAlreadyFulfilledError,
    ReservationAlreadyReleasedError,
    ReservationError,
    ReservationNotFoundError,
)
from src.services.retry_service import (
    RetryError,
    RetryExhaustedError,
    RetryPolicyNotFoundError,
)
from src.services.scheduler_service import (
    InvalidScheduledJobStateError,
    ScheduledJobNotFoundError,
    SchedulerError,
    SchedulerExecutionError,
)
from src.services.template_rendering_service import (
    TemplateNotFoundError,
    TemplateRenderingError,
)
from src.services.workflow_service import WorkflowError


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


def test_opsboard_error_is_exception() -> None:
    assert issubclass(OpsboardError, Exception)


def test_can_raise_and_catch_root() -> None:
    with __import__("pytest").raises(OpsboardError):
        raise OpsboardError("boom")


# ---------------------------------------------------------------------------
# Semantic groups are OpsboardError subtypes
# ---------------------------------------------------------------------------


def test_not_found_error_is_opsboard_error() -> None:
    assert issubclass(NotFoundError, OpsboardError)


def test_conflict_error_is_opsboard_error() -> None:
    assert issubclass(ConflictError, OpsboardError)


def test_invalid_state_error_is_opsboard_error() -> None:
    assert issubclass(InvalidStateError, OpsboardError)


def test_validation_error_is_opsboard_error() -> None:
    assert issubclass(ValidationError, OpsboardError)


# ---------------------------------------------------------------------------
# Inventory exceptions
# ---------------------------------------------------------------------------


def test_inventory_error_chain() -> None:
    assert issubclass(InventoryError, OpsboardError)


def test_product_not_found_caught_as_not_found() -> None:
    exc = ProductNotFoundError(uuid.uuid4())
    assert isinstance(exc, NotFoundError)
    assert isinstance(exc, InventoryError)
    assert isinstance(exc, OpsboardError)


def test_warehouse_not_found_caught_as_not_found() -> None:
    exc = WarehouseNotFoundError(uuid.uuid4())
    assert isinstance(exc, NotFoundError)


def test_negative_stock_caught_as_validation() -> None:
    exc = NegativeStockError(current=5, delta=-10)
    assert isinstance(exc, ValidationError)
    assert isinstance(exc, InventoryError)


# ---------------------------------------------------------------------------
# Reservation exceptions
# ---------------------------------------------------------------------------


def test_reservation_error_chain() -> None:
    assert issubclass(ReservationError, OpsboardError)


def test_reservation_not_found_is_not_found() -> None:
    assert issubclass(ReservationNotFoundError, NotFoundError)


def test_reservation_already_released_is_invalid_state() -> None:
    assert issubclass(ReservationAlreadyReleasedError, InvalidStateError)


def test_reservation_already_fulfilled_is_invalid_state() -> None:
    assert issubclass(ReservationAlreadyFulfilledError, InvalidStateError)


def test_invalid_reservation_quantity_is_validation() -> None:
    assert issubclass(InvalidReservationQuantityError, ValidationError)


def test_insufficient_stock_is_validation() -> None:
    assert issubclass(InsufficientAvailableStockError, ValidationError)


# ---------------------------------------------------------------------------
# Order exceptions
# ---------------------------------------------------------------------------


def test_order_error_chain() -> None:
    assert issubclass(OrderError, OpsboardError)


def test_order_not_found_is_not_found() -> None:
    assert issubclass(OrderNotFoundError, NotFoundError)


def test_duplicate_order_reference_is_conflict() -> None:
    assert issubclass(DuplicateOrderReferenceError, ConflictError)


def test_empty_order_is_validation() -> None:
    assert issubclass(EmptyOrderError, ValidationError)


def test_inactive_reservation_is_invalid_state() -> None:
    assert issubclass(InactiveReservationError, InvalidStateError)


def test_order_quantity_mismatch_is_validation() -> None:
    assert issubclass(OrderQuantityMismatchError, ValidationError)


def test_invalid_order_state_is_invalid_state() -> None:
    assert issubclass(InvalidOrderStateError, InvalidStateError)


# ---------------------------------------------------------------------------
# Analytics exceptions
# ---------------------------------------------------------------------------


def test_analytics_error_chain() -> None:
    assert issubclass(AnalyticsError, OpsboardError)


def test_snapshot_already_exists_is_conflict() -> None:
    assert issubclass(SnapshotAlreadyExistsError, ConflictError)


def test_snapshot_not_found_is_not_found() -> None:
    assert issubclass(SnapshotNotFoundError, NotFoundError)


# ---------------------------------------------------------------------------
# Notification exceptions
# ---------------------------------------------------------------------------


def test_notification_error_chain() -> None:
    assert issubclass(NotificationError, OpsboardError)


def test_notification_not_found_is_not_found() -> None:
    assert issubclass(NotificationNotFoundError, NotFoundError)


def test_invalid_notification_state_is_invalid_state() -> None:
    assert issubclass(InvalidNotificationStateError, InvalidStateError)


# ---------------------------------------------------------------------------
# Cache exceptions
# ---------------------------------------------------------------------------


def test_cache_error_chain() -> None:
    assert issubclass(CacheError, OpsboardError)


def test_cache_serialization_is_validation() -> None:
    assert issubclass(CacheSerializationError, ValidationError)


# ---------------------------------------------------------------------------
# Scheduler exceptions
# ---------------------------------------------------------------------------


def test_scheduler_error_chain() -> None:
    assert issubclass(SchedulerError, OpsboardError)


def test_scheduled_job_not_found_is_not_found() -> None:
    assert issubclass(ScheduledJobNotFoundError, NotFoundError)


def test_invalid_scheduled_job_state_is_invalid_state() -> None:
    assert issubclass(InvalidScheduledJobStateError, InvalidStateError)


def test_scheduler_execution_error_is_opsboard() -> None:
    assert issubclass(SchedulerExecutionError, OpsboardError)


# ---------------------------------------------------------------------------
# Retry exceptions
# ---------------------------------------------------------------------------


def test_retry_error_chain() -> None:
    assert issubclass(RetryError, OpsboardError)


def test_retry_exhausted_is_invalid_state() -> None:
    assert issubclass(RetryExhaustedError, InvalidStateError)


def test_retry_policy_not_found_is_not_found() -> None:
    assert issubclass(RetryPolicyNotFoundError, NotFoundError)


# ---------------------------------------------------------------------------
# Report-job exceptions
# ---------------------------------------------------------------------------


def test_report_job_error_chain() -> None:
    assert issubclass(ReportJobError, OpsboardError)


def test_report_job_not_found_is_not_found() -> None:
    assert issubclass(ReportJobNotFoundError, NotFoundError)


def test_report_request_not_found_is_not_found() -> None:
    assert issubclass(ReportRequestNotFoundError, NotFoundError)


def test_invalid_report_job_state_is_invalid_state() -> None:
    assert issubclass(InvalidReportJobStateError, InvalidStateError)


# ---------------------------------------------------------------------------
# Import exceptions
# ---------------------------------------------------------------------------


def test_bulk_import_error_chain() -> None:
    assert issubclass(BulkImportError, OpsboardError)


def test_malformed_csv_is_validation() -> None:
    assert issubclass(MalformedCsvError, ValidationError)


def test_unknown_product_is_validation() -> None:
    assert issubclass(UnknownProductError, ValidationError)


def test_unknown_warehouse_is_validation() -> None:
    assert issubclass(UnknownWarehouseError, ValidationError)


def test_invalid_import_quantity_is_validation() -> None:
    assert issubclass(InvalidImportQuantityError, ValidationError)


# ---------------------------------------------------------------------------
# Template rendering exceptions
# ---------------------------------------------------------------------------


def test_template_rendering_error_chain() -> None:
    assert issubclass(TemplateRenderingError, OpsboardError)


def test_template_not_found_is_not_found() -> None:
    assert issubclass(TemplateNotFoundError, NotFoundError)


# ---------------------------------------------------------------------------
# Workflow exceptions
# ---------------------------------------------------------------------------


def test_workflow_error_chain() -> None:
    assert issubclass(WorkflowError, OpsboardError)


# ---------------------------------------------------------------------------
# Broad-catch semantics — any service error is catchable as OpsboardError
# ---------------------------------------------------------------------------


def test_broad_catch_covers_all_service_errors() -> None:
    """Raising any leaf exception can be caught as OpsboardError."""
    leaf_instances = [
        ProductNotFoundError(uuid.uuid4()),
        NegativeStockError(0, -1),
        ReservationNotFoundError(uuid.uuid4()),
        InsufficientAvailableStockError(5, 3),
        OrderNotFoundError(uuid.uuid4()),
        DuplicateOrderReferenceError("REF-1"),
        SnapshotAlreadyExistsError(__import__("datetime").date(2026, 1, 1)),
        CacheSerializationError("key"),
        MalformedCsvError("bad csv"),
        TemplateNotFoundError("tmpl"),
        WorkflowError("step failed"),
    ]
    for exc in leaf_instances:
        assert isinstance(exc, OpsboardError), (
            f"{type(exc).__name__} is not an OpsboardError"
        )
