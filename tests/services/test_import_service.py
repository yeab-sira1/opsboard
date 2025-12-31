"""Tests for :class:`ImportService`."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.models import DomainEventType, ImportJobStatus
from src.services import (
    EventService,
    ImportService,
    InventoryService,
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


def _seed_catalog(inventory: InventoryService) -> None:
    inventory.add_product(sku="SKU-1", name="Widget", unit="pcs")
    inventory.add_product(sku="SKU-2", name="Gadget", unit="pcs")
    inventory.create_warehouse(code="WH-1", name="Main", location="B")
    inventory.create_warehouse(code="WH-2", name="Annex", location="M")


CSV_HEADER = "sku,warehouse_code,quantity\n"


def test_preview_parses_without_mutating(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    csv_text = CSV_HEADER + "SKU-1,WH-1,10\nSKU-2,WH-2,5\n"

    rows = imports.preview_stock_csv(csv_text)
    assert [(r.sku, r.warehouse_code, r.quantity) for r in rows] == [
        ("SKU-1", "WH-1", 10),
        ("SKU-2", "WH-2", 5),
    ]
    # Nothing written.
    product = inventory.get_product_by_sku("SKU-1")
    warehouse = inventory.get_warehouse_by_code("WH-1")
    assert inventory.get_stock(product.id, warehouse.id) == 0


def test_successful_import_sets_stock_and_records_event(
    inventory: InventoryService,
    imports: ImportService,
    events: EventService,
) -> None:
    _seed_catalog(inventory)
    csv_text = CSV_HEADER + "SKU-1,WH-1,10\nSKU-2,WH-2,5\n"

    job = imports.import_stock_csv(csv_text, "upload.csv")
    assert job.status is ImportJobStatus.COMPLETED
    assert job.row_count == 2

    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")
    assert inventory.get_stock(p1.id, w1.id) == 10
    assert len(events.get_events_by_type(DomainEventType.STOCK_IMPORTED)) == 1


def test_import_creates_missing_stock_records(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    p1 = inventory.get_product_by_sku("SKU-1")
    w1 = inventory.get_warehouse_by_code("WH-1")
    assert inventory.get_stock(p1.id, w1.id) == 0  # no record yet

    imports.import_stock_csv(CSV_HEADER + "SKU-1,WH-1,7\n", "upload.csv")
    assert inventory.get_stock(p1.id, w1.id) == 7


def test_unknown_product_fails_import(
    inventory: InventoryService,
    imports: ImportService,
    events: EventService,
) -> None:
    _seed_catalog(inventory)
    job = imports.import_stock_csv(
        CSV_HEADER + "NOPE,WH-1,5\n", "upload.csv"
    )

    assert job.status is ImportJobStatus.FAILED
    assert "NOPE" in job.error_message
    assert (
        len(events.get_events_by_type(DomainEventType.STOCK_IMPORT_FAILED))
        == 1
    )


def test_unknown_warehouse_fails_import(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    job = imports.import_stock_csv(
        CSV_HEADER + "SKU-1,NOPE,5\n", "upload.csv"
    )
    assert job.status is ImportJobStatus.FAILED
    assert "NOPE" in job.error_message


def test_negative_quantity_fails_import(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    job = imports.import_stock_csv(
        CSV_HEADER + "SKU-1,WH-1,-3\n", "upload.csv"
    )
    assert job.status is ImportJobStatus.FAILED


def test_malformed_csv_fails_import(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    job = imports.import_stock_csv(
        "sku,warehouse_code\nSKU-1,WH-1\n", "bad.csv"
    )
    assert job.status is ImportJobStatus.FAILED


def test_get_jobs_by_status(
    inventory: InventoryService, imports: ImportService
) -> None:
    _seed_catalog(inventory)
    imports.import_stock_csv(CSV_HEADER + "SKU-1,WH-1,1\n", "ok.csv")
    imports.import_stock_csv(CSV_HEADER + "NOPE,WH-1,1\n", "bad.csv")

    assert len(imports.get_jobs_by_status(ImportJobStatus.COMPLETED)) == 1
    assert len(imports.get_jobs_by_status(ImportJobStatus.FAILED)) == 1
