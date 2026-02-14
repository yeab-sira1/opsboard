"""Tests for retry and backoff value objects."""

from __future__ import annotations

import pytest

from src.models import RetryStrategy
from src.value_objects import BackoffConfig, RetryConfig


def test_retry_config_properties() -> None:
    config = RetryConfig(RetryStrategy.LINEAR, max_attempts=3, base_delay_seconds=5)
    assert config.strategy is RetryStrategy.LINEAR
    assert config.max_attempts == 3
    assert config.base_delay_seconds == 5


def test_retry_config_equality() -> None:
    a = RetryConfig(RetryStrategy.LINEAR, 3, 5)
    b = RetryConfig(RetryStrategy.LINEAR, 3, 5)
    c = RetryConfig(RetryStrategy.EXPONENTIAL, 3, 5)
    assert a == b
    assert a != c
    assert a.__eq__("x") is NotImplemented


def test_retry_config_validation() -> None:
    with pytest.raises(ValueError):
        RetryConfig(RetryStrategy.LINEAR, max_attempts=0, base_delay_seconds=5)
    with pytest.raises(ValueError):
        RetryConfig(RetryStrategy.LINEAR, max_attempts=3, base_delay_seconds=-1)


def test_retry_config_repr() -> None:
    config = RetryConfig(RetryStrategy.IMMEDIATE, 1, 0)
    assert "IMMEDIATE" in repr(config)


def test_backoff_config_properties_and_equality() -> None:
    a = BackoffConfig(RetryStrategy.EXPONENTIAL, 10)
    b = BackoffConfig(RetryStrategy.EXPONENTIAL, 10)
    assert a.strategy is RetryStrategy.EXPONENTIAL
    assert a.base_delay_seconds == 10
    assert a == b
    assert a.__eq__(42) is NotImplemented


def test_backoff_config_validation_and_repr() -> None:
    with pytest.raises(ValueError):
        BackoffConfig(RetryStrategy.LINEAR, -5)
    assert "LINEAR" in repr(BackoffConfig(RetryStrategy.LINEAR, 5))
