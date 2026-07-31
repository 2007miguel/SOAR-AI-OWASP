from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import AssessmentContext


@runtime_checkable
class AssurancePort(Protocol):
    """Interface between the engine and the assurance plane.

    The engine emits a checklist and waits; it never executes security tools.
    In Etapa 0, ManualAdapter handles both sides (human attestation via the API).
    In later stages, the assurance-coordinator implements this port over the network.
    """

    def emit_checklist(self, ctx: AssessmentContext) -> AssessmentContext:
        """Populate ctx.assurance.checklist from ctx.controls.critical_required."""
        ...

    def is_ready(self, ctx: AssessmentContext) -> bool:
        """Return True when all critical controls have an attestation."""
        ...
