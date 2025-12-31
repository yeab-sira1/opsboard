"""Import service: a second, CSV-driven write path into inventory."""

from __future__ import annotations

import csv
import io
import uuid
from typing import NamedTuple

from sqlalchemy.orm import Session

from src.models.domain_event import DomainEventType
from src.models.import_job import ImportJob, ImportJobStatus
from src.repositories import ImportJobRepository
from src.services.event_service import EventService
from src.services.inventory_service import InventoryService

REQUIRED_COLUMNS = ("sku", "warehouse_code", "quantity")


class StockImportRow(NamedTuple):
    """One parsed row of a stock import CSV."""

    sku: str
    warehouse_code: str
    quantity: int


class BulkImportError(Exception):
    """Base class for recoverable import failures (captured on the job)."""


class MalformedCsvError(BulkImportError):
    """Raised when the CSV is structurally invalid."""


class UnknownProductError(BulkImportError):
    """Raised when a row references an unknown product SKU."""

    def __init__(self, sku: str) -> None:
        super().__init__(f"Unknown product SKU: {sku}")
        self.sku = sku


class UnknownWarehouseError(BulkImportError):
    """Raised when a row references an unknown warehouse code."""

    def __init__(self, warehouse_code: str) -> None:
        super().__init__(f"Unknown warehouse code: {warehouse_code}")
        self.warehouse_code = warehouse_code


class InvalidImportQuantityError(BulkImportError):
    """Raised when a row carries a negative quantity."""

    def __init__(self, quantity: int) -> None:
        super().__init__(f"Quantity must not be negative: {quantity}")
        self.quantity = quantity


class ImportService:
    """Imports stock levels from CSV strings into inventory.

    Imports are all-or-nothing: every row is parsed and resolved before any
    stock is written, so a failure on any row leaves inventory untouched. Stock
    is written exclusively through :class:`InventoryService`; outcomes are
    recorded as domain events via :class:`EventService`.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._jobs = ImportJobRepository(session)
        self._inventory = InventoryService(session)
        self._events = EventService(session)

    def preview_stock_csv(self, csv_string: str) -> list[StockImportRow]:
        """Parse and return the rows a CSV would import, without writing."""
        return self._parse(csv_string)

    def import_stock_csv(
        self, csv_string: str, source_name: str
    ) -> ImportJob:
        """Import stock levels from ``csv_string`` atomically.

        Returns the resulting :class:`ImportJob`; on any failure the job is
        marked ``FAILED`` with a captured message and no stock is changed.
        """
        job = self._jobs.add(
            ImportJob(
                source_name=source_name,
                row_count=0,
                status=ImportJobStatus.PENDING,
            )
        )
        try:
            rows = self._parse(csv_string)
            job.row_count = len(rows)
            resolved = self._resolve(rows)
            for product_id, warehouse_id, quantity in resolved:
                self._inventory.set_stock(product_id, warehouse_id, quantity)
        except BulkImportError as exc:
            job.status = ImportJobStatus.FAILED
            job.error_message = str(exc)
            self._events.record_event(
                DomainEventType.STOCK_IMPORT_FAILED,
                {"job_id": str(job.id), "source_name": source_name},
            )
            self._session.flush()
            return job

        job.status = ImportJobStatus.COMPLETED
        self._events.record_event(
            DomainEventType.STOCK_IMPORTED,
            {"job_id": str(job.id), "row_count": job.row_count},
        )
        self._session.flush()
        return job

    def get_jobs_by_status(
        self, status: ImportJobStatus
    ) -> list[ImportJob]:
        """Return all import jobs in the given ``status``."""
        return self._jobs.get_by_status(status)

    @staticmethod
    def _parse(csv_string: str) -> list[StockImportRow]:
        reader = csv.DictReader(io.StringIO(csv_string))
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS).issubset(
            reader.fieldnames
        ):
            raise MalformedCsvError(
                f"CSV must have columns: {', '.join(REQUIRED_COLUMNS)}"
            )

        rows: list[StockImportRow] = []
        for line_number, raw in enumerate(reader, start=2):
            sku = (raw.get("sku") or "").strip()
            warehouse_code = (raw.get("warehouse_code") or "").strip()
            quantity_raw = (raw.get("quantity") or "").strip()
            if not sku or not warehouse_code or not quantity_raw:
                raise MalformedCsvError(
                    f"Missing value on line {line_number}"
                )
            try:
                quantity = int(quantity_raw)
            except ValueError as exc:
                raise MalformedCsvError(
                    f"Invalid quantity on line {line_number}: {quantity_raw!r}"
                ) from exc
            rows.append(StockImportRow(sku, warehouse_code, quantity))
        return rows

    def _resolve(
        self, rows: list[StockImportRow]
    ) -> list[tuple[uuid.UUID, uuid.UUID, int]]:
        resolved: list[tuple[uuid.UUID, uuid.UUID, int]] = []
        for row in rows:
            product = self._inventory.get_product_by_sku(row.sku)
            if product is None:
                raise UnknownProductError(row.sku)
            warehouse = self._inventory.get_warehouse_by_code(
                row.warehouse_code
            )
            if warehouse is None:
                raise UnknownWarehouseError(row.warehouse_code)
            if row.quantity < 0:
                raise InvalidImportQuantityError(row.quantity)
            resolved.append((product.id, warehouse.id, row.quantity))
        return resolved
