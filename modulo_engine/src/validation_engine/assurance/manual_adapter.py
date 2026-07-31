from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.assurance import ChecklistItem
from ..contracts.enums import AttestationStatus
from ..kb.service import KBService


class ManualAdapter:
    """Etapa 0: 100% manual attestation.

    emit_checklist builds the checklist from M5's critical controls.
    Attestations arrive later via the API (POST /assessments/{id}/attest).
    The engine resumes when all critical controls are attested.
    """

    def __init__(self, kb: KBService) -> None:
        self._kb = kb

    def emit_checklist(self, ctx: AssessmentContext) -> AssessmentContext:
        for ctrl in ctx.controls.critical_required:
            ctx.assurance.checklist.append(
                ChecklistItem(
                    control_id=ctrl.control_id,
                    why=ctrl.required_by_asi,
                    category=ctrl.category,
                    suggested_assur=self._suggested_assur(ctrl.required_by_asi),
                    status=AttestationStatus.NOT_IMPLEMENTED,
                )
            )
        return ctx

    def _suggested_assur(self, required_by_asi: list[str]) -> list[str]:
        """ASSUR-IDs relevant to the ASIs that mandate this control (plan Módulo 6.2):
        active_asi → assurance_methods.covers_risks → ASSUR-IDs. Non-ASI tokens
        (e.g. 'baseline', 'high_risk_domain') yield no methods."""
        methods: set[str] = set()
        for asi_id in required_by_asi:
            methods.update(self._kb.assurance_methods_for_asi(asi_id))
        return sorted(methods)

    def is_ready(self, ctx: AssessmentContext) -> bool:
        critical_ids = {c.control_id for c in ctx.controls.critical_required}
        return critical_ids.issubset(set(ctx.assurance.attestations.keys()))
