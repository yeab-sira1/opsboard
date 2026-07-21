"""Centralized logging configuration for opsboard.

Usage::

    from src.config.logging import configure_logging, get_logger

    configure_logging()          # call once at application startup
    logger = get_logger(__name__)
    logger.info("ready")

:func:`configure_logging` is idempotent — calling it multiple times does not
duplicate handlers or change an already-configured setup.
"""

from __future__ import annotations

import logging

from src.config.setting import settings

_HANDLER_NAME = "opsboard_console"
_ROOT_LOGGER = "opsboard"


def configure_logging(log_level: str | None = None) -> None:
    """Configure the ``opsboard`` logger with a single console handler.

    The effective level is taken from *log_level* when supplied, otherwise
    from :attr:`~src.config.setting.Settings.log_level`.  The function is
    idempotent: repeated calls with the same (or no) arguments do not add
    extra handlers.

    Parameters
    ----------
    log_level:
        Override the level from settings, e.g. ``"DEBUG"``.  Must be a valid
        :mod:`logging` level name.
    """
    level_name = (log_level or settings.log_level).upper()
    level = logging.getLevelName(level_name)

    logger = logging.getLogger(_ROOT_LOGGER)

    # Guard: if a handler with our sentinel name is already attached, the
    # logger was already configured — update the level and return.
    for handler in logger.handlers:
        if handler.get_name() == _HANDLER_NAME:
            logger.setLevel(level)
            handler.setLevel(level)
            return

    logger.setLevel(level)
    logger.propagate = False

    handler = logging.StreamHandler()
    handler.set_name(_HANDLER_NAME)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``opsboard`` namespace.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.  If the value already
        starts with ``"opsboard."``, it is used verbatim; otherwise it is
        prefixed so all loggers remain under the shared hierarchy.

    Returns
    -------
    logging.Logger
        A logger whose effective level and handlers are inherited from the
        ``opsboard`` root logger configured by :func:`configure_logging`.
    """
    if name.startswith(f"{_ROOT_LOGGER}.") or name == _ROOT_LOGGER:
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER}.{name}")
