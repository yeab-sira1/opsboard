# OpsBoard

Internal operations and inventory platform for managing stock, reservations, orders,
analytics, and reporting. OpsBoard models the full lifecycle from raw CSV stock imports
through reservation holds, order fulfilment, scheduled reporting, and immutable audit
trails — all wired together through a layered service architecture.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Domain Overview](#domain-overview)
4. [Key Workflows](#key-workflows)
5. [Development Setup](#development-setup)
6. [Testing](#testing)
7. [Docker](#docker)

---

## Architecture

OpsBoard follows a strict domain-layered architecture. Each layer has a single
responsibility and depends only on layers below it.

```
┌─────────────────────────────────────────────────────────────┐
│                      Entry Points                           │
│           (tests, CLI, future API surface)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                     Services Layer                          │
│  InventoryService  ReservationService  OrderService         │
│  AnalyticsService  ReportJobService    SchedulerService      │
│  RetryService      WorkflowService     NotificationService  │
│  ImportService     ExportService       AuditService         │
│  CacheService      EventService        DashboardService     │
│  BatchReportService  BatchExportService  BackoffService     │
│  TemplateRenderingService                                   │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
┌──────────▼──────────┐  ┌────────────▼──────────────────────┐
│  Schemas / Value    │  │        Repositories Layer          │
│  Objects            │  │  ProductRepository                 │
│  (Pydantic input/   │  │  WarehouseRepository               │
│   output contracts, │  │  StockRecordRepository             │
│   immutable VOs)    │  │  ReservationRepository             │
└─────────────────────┘  │  OrderRepository                   │
                         │  DomainEventRepository             │
                         │  ImportJobRepository               │
                         │  ScheduledJobRepository            │
                         │  RetryAttempt/PolicyRepository     │
                         │  WorkflowExecutionRepository       │
                         │  AuditEntryRepository              │
                         │  CacheRepository                   │
                         │  NotificationRepository (+ categ.) │
                         │  ReportRequest/Job/BundleRepository│
                         │  DailyInventorySnapshotRepository  │
                         └──────────────┬────────────────────┘
                                        │
                         ┌──────────────▼────────────────────┐
                         │          Models Layer              │
                         │  SQLAlchemy ORM declarative models │
                         │  mapped to a single SQLite/        │
                         │  configurable engine via           │
                         │  src/config/database.py            │
                         └───────────────────────────────────┘
```

**Major domains:**
Inventory · Reservations · Orders · Analytics · Reporting · Notifications ·
Scheduling · Events · Cache · Import · Search · Retry/Backoff · Workflows · Audit

---

## Project Structure

```
src/
├── config/             Database engine and session factory configuration
├── models/             SQLAlchemy ORM models — one file per entity
├── repositories/       Repository pattern wrappers around ORM queries;
│                       one repository class per model
├── schemas/            Pydantic input/output schemas for service boundaries
│                       (e.g. WorkflowRequest, RetryRequest, BatchReportResult)
├── services/           Business logic; services depend on repositories,
│                       never on each other's internals directly
├── value_objects/      Immutable dataclasses used as typed parameters
│                       (DateRange, Pagination, SortSpec, BackoffConfig, …)
└── search/             Search helpers for filtered, paginated entity queries

tests/
├── conftest.py         Shared fixtures (in-memory SQLite session, factories)
├── test_models.py      Smoke tests for model registration and relationships
├── models/             Per-model unit tests
├── repositories/       Repository layer tests (SQLite in-memory)
├── schemas/            Pydantic schema validation tests
├── value_objects/      Value object invariant tests
├── services/           Service unit tests with real in-memory SQLite
├── search/             Search and filter tests
└── integration/        End-to-end workflow tests spanning multiple services
```

---

## Domain Overview

| Entity | Description |
|---|---|
| `Product` | Stockable item with a unique SKU |
| `Warehouse` | Physical location that holds stock |
| `StockRecord` | Current on-hand quantity for a product/warehouse pair |
| `Reservation` | Stock hold that reduces available quantity |
| `Order` | Committed fulfilment of one or more reservations |
| `DomainEvent` | Immutable business event record emitted by services |
| `ImportJob` | Bulk CSV stock import record with status tracking |
| `ScheduledJob` | Synchronously executed scheduled task |
| `RetryAttempt` | Single execution record for a retried operation |
| `RetryPolicy` | Named retry strategy configuration (strategy, max attempts, delays) |
| `WorkflowExecution` | Orchestrated multi-step workflow run with step results |
| `AuditEntry` | Immutable state-change history record with before/after payload |
| `CacheEntry` | Persisted JSON key-value cache with optional TTL |
| `DailyInventorySnapshot` | Point-in-time inventory position captured per day |
| `NotificationTemplate` | Reusable subject/body message template |
| `ReportRequest` | User-facing request for a generated report |
| `ReportJob` | Internal job record for report generation |
| `ReportBundle` | Packaged collection of report output files |
| `Organization` | Tenant-level grouping for users and products |
| `Role` / `User` | RBAC primitives for access control |

---

## Key Workflows

### 1. Stock Import → Fulfilment

```
CSV upload
  └─► ImportService          parses rows, validates SKUs/warehouses
        └─► InventoryService  upserts StockRecord quantities
              └─► ReservationService  creates stock holds
                    └─► OrderService       commits order lines
                          └─► AnalyticsService  records DailyInventorySnapshot
                                └─► ExportService  serialises output CSV
```

### 2. Retry → Scheduler → Events

```
Failed job detected
  └─► RetryService       evaluates RetryPolicy, records RetryAttempt
        └─► BackoffService  computes delay (fixed / linear / exponential)
              └─► SchedulerService  enqueues ScheduledJob
                    └─► EventService  emits DomainEvent on completion/failure
```

### 3. Report Request → Notification → Events

```
ReportRequest created
  └─► ReportJobService   creates ReportJob, transitions status
        └─► SchedulerService    picks up ScheduledJob for generation
              └─► NotificationService  renders template, creates Notification
                    └─► EventService       emits report-ready DomainEvent
```

### 4. Workflow Orchestration → Audit Trail

```
WorkflowService.run(request)
  └─► executes ordered WorkflowStep list
        └─► each step result stored in WorkflowExecution.step_results
              └─► AuditService  writes AuditEntry for every state transition
                    └─► CacheService  stores intermediate results by key
```

---

## Development Setup

Python 3.12 is required. The project uses [uv](https://docs.astral.sh/uv/) for
environment and dependency management.

```bash
# Install uv (if not already installed)
pip install uv

# Create the virtualenv and install all dependencies (including dev group)
uv sync

# Run the test suite
uv run pytest
```

The `uv.lock` file pins every transitive dependency. Run `uv sync --frozen` to
reproduce the exact environment recorded in the lock file.

### Environment notes

- The database defaults to an in-memory SQLite instance configured in
  `src/config/database.py`. No external services are required.
- A `.python-version` file pins the interpreter to 3.12 for tools that respect it
  (e.g. pyenv, mise).

---

## Testing

### Test categories

| Category | Location | Description |
|---|---|---|
| Model smoke tests | `tests/test_models.py` | Verifies all models register with `Base.metadata` |
| Model unit tests | `tests/models/` | Per-model column, constraint, and relationship checks |
| Schema tests | `tests/schemas/` | Pydantic validation, coercion, and error cases |
| Value object tests | `tests/value_objects/` | Invariant and equality checks for immutable VOs |
| Repository tests | `tests/repositories/` | CRUD and query behaviour against in-memory SQLite |
| Service tests | `tests/services/` | Business logic with real repositories and SQLite |
| Search tests | `tests/search/` | Filter, sort, and pagination behaviour |
| Integration / E2E | `tests/integration/` | Multi-service workflows exercised end-to-end |

### Running tests

```bash
# All tests (coverage enabled by default via pyproject.toml)
uv run pytest

# Explicit coverage report
uv run pytest --cov=src --cov-report=term-missing

# A single test file
uv run pytest tests/integration/test_e2e_order_fulfillment.py -v

# A specific test by name
uv run pytest -k "test_reserve_stock"
```

### E2E integration tests

The `tests/integration/` suite covers the following end-to-end scenarios:

| Test file | Scenario |
|---|---|
| `test_e2e_order_fulfillment.py` | Stock import → reservation → order fulfilment |
| `test_e2e_event_audit_trail.py` | Service actions produce correct DomainEvents and AuditEntries |
| `test_e2e_retry_lifecycle.py` | Retry policy evaluation, backoff, and exhaustion |
| `test_e2e_scheduler_reporting.py` | Report request → job scheduling → notification dispatch |
| `test_e2e_snapshot_comparison.py` | Daily inventory snapshots and analytics aggregation |
| `test_e2e_workflow_orchestration.py` | WorkflowService multi-step execution and audit trail |

---

## Docker

The provided Docker image runs the full test suite. It is intended for CI and
validation environments, not production serving.

```bash
# Build the image
docker build -t opsboard .

# Run the test suite inside the container
docker run opsboard
```

The image uses a two-stage dependency install for layer caching: locked
dependencies are installed before the source tree is copied, so rebuilds after
code-only changes are fast.
