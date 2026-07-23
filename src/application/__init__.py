"""Application / use-case layer for opsboard.

This layer contains thin orchestrators that coordinate multiple services for
common business workflows.  All business logic remains inside the service
layer; application classes only wire calls together.

Available use-case classes:

* :class:`~src.application.order_fulfillment.OrderFulfillmentApp`
* :class:`~src.application.stock_import.StockImportApp`
* :class:`~src.application.reporting.ReportingApp`
"""

from src.application.order_fulfillment import OrderFulfillmentApp
from src.application.reporting import ReportingApp
from src.application.stock_import import StockImportApp

__all__ = [
    "OrderFulfillmentApp",
    "ReportingApp",
    "StockImportApp",
]
