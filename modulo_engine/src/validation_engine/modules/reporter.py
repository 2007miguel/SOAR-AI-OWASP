from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.enums import AttestationStatus
from ..kb.service import KBService


class Reporter:
    """R — Produces the final report from the full Assessment Context.

    Per the read/write matrix (assessment_context.txt §3), the Reporter produces
    an external report and does NOT mutate the context; the orchestrator owns the
    status transition to COMPLETED. run() is the pipeline marker for the report
    step; call build_report(ctx) to get the structured report document.
    """

    name = "reporter"
    reads = ["*"]
    writes: list[str] = []

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        return ctx


def build_report(ctx: AssessmentContext) -> dict:
    """Build the full structured report from a completed AssessmentContext."""
    attestations = ctx.assurance.attestations

    def ctrl_status(ctrl_id: str) -> str:
        att = attestations.get(ctrl_id)
        return att.status.value if att else AttestationStatus.NOT_IMPLEMENTED.value

    critical_ids = [c.control_id for c in ctx.controls.critical_required]
    implemented = [cid for cid in critical_ids if ctrl_status(cid) == AttestationStatus.IMPLEMENTED.value]
    missing = [cid for cid in critical_ids if ctrl_status(cid) == AttestationStatus.NOT_IMPLEMENTED.value]
    partial = [cid for cid in critical_ids if ctrl_status(cid) == AttestationStatus.PARTIAL.value]

    verdict = ctx.verdict
    validation = ctx.analysis.validation
    return {
        "assessment_id": ctx.assessment_id,
        "kb_version": ctx.kb_version,
        "playbook_id": ctx.playbook_id,
        "status": ctx.status.value,
        "errors": validation.errors if validation else [],  # blocking validation errors (M1 abort)
        "verdict": verdict.result.value if verdict else None,
        "verdict_label": verdict.label if verdict else None,
        "verdict_rationale": verdict.rationale if verdict else None,
        "blocking_reasons": verdict.blocking_reasons if verdict else [],
        "active_flags": list(ctx.inputs.capability_flags.active().keys()),
        "active_threats": ctx.analysis.active_threats,
        "active_risks": ctx.analysis.active_asi,
        "high_risk_domain": ctx.analysis.high_risk_domain,
        "hotl_required": ctx.analysis.hotl_required,
        "critical_systems_path": ctx.analysis.critical_systems_path,
        "critical_controls": {
            "required": critical_ids,
            "implemented": implemented,
            "partial": partial,
            "missing": missing,
        },
        "recommended_controls": [
            {
                "control_id": c.control_id,
                "name": c.name,
                "mitigates": c.mitigates,
                "lifecycle_phases": c.lifecycle_phases,
            }
            for c in ctx.controls.recommended
        ],
        "assurance_methods_used": ctx.assurance.assurance_methods_used,
        "warnings": ctx.analysis.warnings,
        "trace": verdict.trace.model_dump() if verdict else {},
    }
