"""Backoff service: deterministic retry-delay calculation."""

from __future__ import annotations

from src.models.retry_policy import RetryStrategy


class BackoffService:
    """Computes retry delays from a strategy and base delay.

    The calculation is pure and deterministic — it never sleeps and has no
    dependency on wall-clock time.
    """

    def calculate_delay(
        self,
        strategy: RetryStrategy,
        base_delay_seconds: int,
        attempt: int,
    ) -> int:
        """Return the delay in seconds before ``attempt``.

        ``attempt`` is 1-indexed. Strategies:

        * ``IMMEDIATE`` → ``0``
        * ``LINEAR`` → ``base_delay_seconds * attempt``
        * ``EXPONENTIAL`` → ``base_delay_seconds * 2 ** (attempt - 1)``
        """
        if attempt < 1:
            raise ValueError(f"attempt must be >= 1, got {attempt}")

        if strategy is RetryStrategy.IMMEDIATE:
            return 0
        if strategy is RetryStrategy.LINEAR:
            return base_delay_seconds * attempt
        return base_delay_seconds * (2 ** (attempt - 1))
