"""Tests for :mod:`src.config.logging`."""

from __future__ import annotations

import logging

import pytest

from src.config.logging import _HANDLER_NAME, _ROOT_LOGGER, configure_logging, get_logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_opsboard_logger() -> None:
    """Remove all handlers from the opsboard root logger so each test starts
    from a clean state without interfering with the global logging hierarchy."""
    root = logging.getLogger(_ROOT_LOGGER)
    root.handlers.clear()
    # Reset child loggers that may have been created during the test
    for name in list(logging.Logger.manager.loggerDict):
        if name.startswith(_ROOT_LOGGER):
            logging.getLogger(name).handlers.clear()


@pytest.fixture(autouse=True)
def isolated_logger():
    """Ensure each test gets a pristine opsboard logger."""
    _reset_opsboard_logger()
    yield
    _reset_opsboard_logger()


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


def test_configure_logging_adds_exactly_one_handler() -> None:
    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert len(root.handlers) == 1


def test_configure_logging_handler_is_stream_handler() -> None:
    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert isinstance(root.handlers[0], logging.StreamHandler)


def test_configure_logging_handler_has_sentinel_name() -> None:
    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert root.handlers[0].get_name() == _HANDLER_NAME


def test_configure_logging_sets_requested_level() -> None:
    configure_logging(log_level="DEBUG")
    root = logging.getLogger(_ROOT_LOGGER)
    assert root.level == logging.DEBUG


def test_configure_logging_defaults_to_settings_level() -> None:
    """Without an explicit override the level comes from settings.log_level."""
    from src.config.setting import settings

    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    expected = logging.getLevelName(settings.log_level.upper())
    assert root.level == expected


def test_configure_logging_does_not_propagate() -> None:
    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert root.propagate is False


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_configure_logging_idempotent_same_call() -> None:
    configure_logging()
    configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert len(root.handlers) == 1


def test_configure_logging_idempotent_multiple_calls() -> None:
    for _ in range(5):
        configure_logging()
    root = logging.getLogger(_ROOT_LOGGER)
    assert len(root.handlers) == 1


def test_configure_logging_idempotent_level_update() -> None:
    """Calling configure_logging again with a different level updates the level
    without adding a second handler."""
    configure_logging(log_level="WARNING")
    configure_logging(log_level="DEBUG")

    root = logging.getLogger(_ROOT_LOGGER)
    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


def test_get_logger_returns_logger_instance() -> None:
    logger = get_logger("mymodule")
    assert isinstance(logger, logging.Logger)


def test_get_logger_is_under_opsboard_namespace() -> None:
    logger = get_logger("mymodule")
    assert logger.name.startswith(_ROOT_LOGGER)


def test_get_logger_prefixes_plain_name() -> None:
    logger = get_logger("services.inventory")
    assert logger.name == f"{_ROOT_LOGGER}.services.inventory"


def test_get_logger_does_not_double_prefix_opsboard_name() -> None:
    logger = get_logger("opsboard.services.inventory")
    assert logger.name == "opsboard.services.inventory"


def test_get_logger_root_name_unchanged() -> None:
    logger = get_logger(_ROOT_LOGGER)
    assert logger.name == _ROOT_LOGGER


def test_get_logger_child_inherits_level_from_root() -> None:
    configure_logging(log_level="WARNING")
    child = get_logger("test.child")
    # Effective level is inherited; child itself has NOTSET (0)
    assert child.getEffectiveLevel() == logging.WARNING


# ---------------------------------------------------------------------------
# Public re-export from src.config
# ---------------------------------------------------------------------------


def test_config_package_exports_configure_logging() -> None:
    from src.config import configure_logging as fn  # noqa: F401

    assert callable(fn)


def test_config_package_exports_get_logger() -> None:
    from src.config import get_logger as fn  # noqa: F401

    assert callable(fn)
