"""Tests for :class:`BackoffService`."""

from __future__ import annotations

import pytest

from src.models import RetryStrategy
from src.services import BackoffService


@pytest.fixture
def backoff() -> BackoffService:
    return BackoffService()


def test_immediate_strategy_is_always_zero(backoff: BackoffService) -> None:
    for attempt in (1, 2, 5):
        assert backoff.calculate_delay(
            RetryStrategy.IMMEDIATE, 10, attempt
        ) == 0


def test_linear_strategy(backoff: BackoffService) -> None:
    assert backoff.calculate_delay(RetryStrategy.LINEAR, 5, 1) == 5
    assert backoff.calculate_delay(RetryStrategy.LINEAR, 5, 2) == 10
    assert backoff.calculate_delay(RetryStrategy.LINEAR, 5, 3) == 15


def test_exponential_strategy(backoff: BackoffService) -> None:
    assert backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 5, 1) == 5
    assert backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 5, 2) == 10
    assert backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 5, 3) == 20
    assert backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 5, 4) == 40


def test_delay_is_deterministic(backoff: BackoffService) -> None:
    a = backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 3, 4)
    b = backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 3, 4)
    assert a == b


def test_zero_base_delay(backoff: BackoffService) -> None:
    assert backoff.calculate_delay(RetryStrategy.LINEAR, 0, 5) == 0
    assert backoff.calculate_delay(RetryStrategy.EXPONENTIAL, 0, 5) == 0


def test_invalid_attempt_raises(backoff: BackoffService) -> None:
    with pytest.raises(ValueError):
        backoff.calculate_delay(RetryStrategy.LINEAR, 5, 0)
