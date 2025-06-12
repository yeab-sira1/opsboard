# opsboard

Internal operations and inventory platform.

opsboard is an internal tool for managing organizations, their members, and the
day-to-day operational data that supports inventory and fulfilment workflows.

## Layout

```text
src/
  config/        Engine and session configuration
  models/        SQLAlchemy ORM models
  repositories/  Persistence helpers (repository pattern)
  services/      Application/business logic
tests/           Test suite
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for environment and
dependency management.

```bash
uv sync          # create the virtualenv and install dependencies
uv run pytest    # run the test suite
```

Requires Python 3.12.
