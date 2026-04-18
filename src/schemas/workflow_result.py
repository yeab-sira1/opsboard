"""Workflow result schema."""

from __future__ import annotations

from typing import NamedTuple

from src.value_objects.workflow_step import WorkflowStep


class WorkflowResult(NamedTuple):
    """The outcome of running a workflow, with its per-step record."""

    successful: bool
    steps: list[WorkflowStep]

    @property
    def step_count(self) -> int:
        """The number of steps that ran."""
        return len(self.steps)

    def failed_steps(self) -> list[WorkflowStep]:
        """Return the steps that did not succeed."""
        return [step for step in self.steps if not step.successful]
