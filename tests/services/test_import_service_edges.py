"""Edge-case, validation, and rollback tests for :class:`ImportService`."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models import DomainEventType, ImportJobStatus
from src.services import (
    EventService,
    ImportService,
    InventoryService,
    MalformedCsvError,
)


@pytest.fixture
def inventory(session: Session) -> InventoryService:
    return InventoryService(session)


@pytest.fixture
def events(session: Session) -> EventService:
    return EventService(session)


@pytest.fixture
def imports(session: Session) -> ImportService:
    return ImportService(session)


CSV_HEADER = "sku,warehouse_code,quantity\n"


def _seed(inventory: InventoryService) -> None:
    inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    inventory.add_product(sku="SKU-2", name="Gadget", unit="pcs")
    inventory.create_warehouse(code="WH-1", name="Main", location="B")


def test_failure_rolls_back_all_rows(
    inventory: InventoryService,
    imports: ImportService,
    events: EventService,
) -> None:
    _seed(inventory)
    # First row is valid; second references an unknown product.
    csv_text = CSV_HEADER + "SKU-1,WH-1,5\nNOPE,WH-1,9\n"

    job = imports.import_stock_csv(csv_text, "upload.csv")
    assert job.status is ImportJobStatus.FAILED

    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")
    # The valid first row must NOT have been applied (no partial success).
    assert inventory.get_stock(p1.id, w1.id) == 0
    assert events.get_events_by_type(DomainEventType.STOCK_IMPORTED) == []


def test_repeated_imports_overwrite_stock(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")

    imports.import_stock_csv(CSV_HEADER + "SKU-1,WH-1,5\n", "first.csv")
    assert inventory.get_stock(p1.id, w1.id) == 5

    imports.import_stock_csv(CSV_HEADER + "SKU-1,WH-1,8\n", "second.csv")
    assert inventory.get_stock(p1.id, w1.id) == 8
    assert len(imports.get_jobs_by_status(ImportJobStatus.COMPLETED)) == 2


def test_non_integer_quantity_fails(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    job = imports.import_stock_csv(
        CSV_HEADER + "SKU-1,WH-1,abc\n", "bad.csv"
    )
    assert job.status is ImportJobStatus.FAILED
    assert "quantity" in job.error_message.lower()


def test_blank_value_fails(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    job = imports.import_stock_csv(CSV_HEADER + "SKU-1,,5\n", "bad.csv")
    assert job.status is ImportJobStatus.FAILED


def test_empty_csv_completes_with_zero_rows(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    job = imports.import_stock_csv(CSV_HEADER, "empty.csv")
    assert job.status is ImportJobStatus.COMPLETED
    assert job.row_count == 0


def test_extra_columns_are_ignored(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    csv_text = "sku,warehouse_code,quantity,note\nSKU-1,WH-1,4,hello\n"
    job = imports.import_stock_csv(csv_text, "extra.csv")

    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")
    assert job.status is ImportJobStatus.COMPLETED
    assert inventory.get_stock(p1.id, w1.id) == 4


def test_preview_raises_on_missing_columns(
    imports: ImportService,
) -> None:
    with pytest.raises(MalformedCsvError):
        imports.preview_stock_csv("sku,quantity\nSKU-1,5\n")


def test_preview_of_empty_csv_returns_no_rows(
    imports: ImportService,
) -> None:
    assert imports.preview_stock_csv(CSV_HEADER) == []


def test_whitespace_is_trimmed(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed(inventory)
    job = imports.import_stock_csv(
        CSV_HEADER + " SKU-1 , WH-1 , 6 \n", "ws.csv"
    )
    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")
    assert job.status is ImportJobStatus.COMPLETED
    assert inventory.get_stock(p1.id, w1.id) == 6
