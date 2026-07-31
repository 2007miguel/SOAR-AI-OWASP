from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import AssessmentContext


@runtime_checkable
class AssessmentStore(Protocol):
    """Interface for persisting and retrieving AssessmentContext objects.

    The engine calls save() after run() (AWAITING_ASSURANCE) and update()
    after resume() (COMPLETED). The API calls get() to reload a case between
    the two phases.
    """

    def save(self, ctx: AssessmentContext) -> None:
        """Persist a new assessment. Raises if assessment_id already exists."""
        ...

    def get(self, assessment_id: str) -> AssessmentContext | None:
        """Load an assessment by ID. Returns None if not found."""
        ...

    def update(self, ctx: AssessmentContext) -> None:
        """Overwrite an existing assessment. Raises KeyError if not found."""
        ...
