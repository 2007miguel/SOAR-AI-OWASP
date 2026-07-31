from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.analysis import ArchitectureRecos
from ..kb.service import KBService


class M4ContextEscalator:
    name = "m4_context_escalator"
    reads = ["inputs.business_context", "analysis.active_asi"]
    writes = [
        "analysis.high_risk_domain",
        "analysis.hotl_required",
        "analysis.architecture_recos",
        "analysis.escalations",
    ]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        domain = ctx.inputs.business_context.business_domain.value
        arch_id = ctx.inputs.business_context.architecture_id.value
        escalations: list[dict] = []

        # High-risk domain escalation (EU AI Act Annex domains)
        high_risk = domain in kb.high_risk_domains()
        if high_risk:
            escalations.append({
                "rule": f"business_domain '{domain}' classified as high-risk (EU AI Act Annex)",
                "effect": "CTRL-DEP-05 added to critical controls; Human-Over-The-Loop required",
            })

        # Architecture recommendations — informative only, does NOT add threats or ASI to verdict
        recos = kb.architecture_recommendations(arch_id)

        ctx.analysis.high_risk_domain = high_risk
        ctx.analysis.hotl_required = high_risk
        ctx.analysis.architecture_recos = ArchitectureRecos(
            security_practices=recos["security_practices"],
            priority_control_domains=recos["priority_control_domains"],
        )
        ctx.analysis.escalations = escalations

        return ctx
