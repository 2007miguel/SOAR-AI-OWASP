from __future__ import annotations

from ..contracts import AssessmentContext
from ..kb.service import KBService


class M3RiskMapper:
    name = "m3_risk_mapper"
    reads = ["analysis.active_threats"]
    writes = ["analysis.active_asi", "analysis.asi_trace"]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        # T9 has maps_to_asi=[] by design (not in OWASP Appendix A).
        # It contributes no ASI-IDs but remains an active threat with controls.
        asi_trace: dict[str, list[str]] = {}

        for tid in ctx.analysis.active_threats:
            for asi_id in kb.maps_to_asi(tid):
                asi_trace.setdefault(asi_id, [])
                if tid not in asi_trace[asi_id]:
                    asi_trace[asi_id].append(tid)

        ctx.analysis.active_asi = sorted(asi_trace.keys())
        ctx.analysis.asi_trace = asi_trace

        return ctx
