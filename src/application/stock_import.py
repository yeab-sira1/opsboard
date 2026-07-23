"""Stock-import use-case orchestrator.

Coordinates :class:`~src.services.ImportService` and
:class:`~src.services.InventoryService` for the CSV import workflow.
"""

from __future__ import annotations

from src.container import Container
from src.models.import_job import ImportJob
from src.models.product import Product
from src.models.warehouse import Warehouse
from src.services.import_service import StockImportRow


class StockImportApp:
    """Orchestrates stock imports and inventory setup.

    Parameters
    ----------
    container:
        A :class:`~src.container.Container` bound to the current session.
    """

    def __init__(self, container: Container) -> None:
        self._c = container

    def setup_catalog(
        self,
        sku: str,
        name: str,
        unit: str,
        warehouse_code: str,
        warehouse_name: str,
        warehouse_location: str,
    ) -> tuple[Product, Warehouse]:
        """Create a product and warehouse pair ready for stock imports.

        Convenience method for bootstrapping a catalog entry in one call.

        Parameters
        ----------
        sku:
            Unique product stock-keeping unit.
        name:
            Human-readable product name.
        unit:
            Unit of measure (e.g. ``"pcs"``, ``"kg"``).
        warehouse_code:
            Unique warehouse identifier code.
        warehouse_name:
            Human-readable warehouse name.
        warehouse_location:
            Physical location string.
        """
        product = self._c.inventory.add_product(
            sku=sku, name=name, unit=unit
        )
        warehouse = self._c.inventory.create_warehouse(
            code=warehouse_code,
            name=warehouse_name,
            location=warehouse_location,
        )
        return product, warehouse

    def import_csv(self, csv_string: str, source_name: str) -> ImportJob:
        """Run a CSV stock import and return the resulting job record.

        Parameters
        ----------
        csv_string:
            Raw CSV content with ``sku``, ``warehouse_code``, and
            ``quantity`` columns.
        source_name:
            Descriptive label for the import source, recorded on the job.
        """
        return self._c.imports.import_stock_csv(csv_string, source_name)

    def preview_csv(self, csv_string: str) -> list[StockImportRow]:
        """Parse a CSV and return rows without writing to the database.

        Parameters
        ----------
        csv_string:
            Raw CSV content to validate.
        """
        return self._c.imports.preview_stock_csv(csv_string)
