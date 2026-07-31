from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.controls import CriticalControl, RecommendedControl
from ..kb.models import Control
from ..kb.service import KBService

# Maps control_id prefix → domain category label
_CTRL_CATEGORY: dict[str, str] = {
    "CTRL-AUTH": "authentication_authorization",
    "CTRL-DATA": "data_protection",
    "CTRL-PROMPT": "prompt_security",
    "CTRL-TOOL": "tool_execution",
    "CTRL-INTERAGENT": "inter_agent_communication",
    "CTRL-SC": "supply_chain",
    "CTRL-MON": "monitoring_logging",
    "CTRL-DEP": "deployment_hardening",
}


def _category(control_id: str) -> str:
    for prefix, cat in _CTRL_CATEGORY.items():
        if control_id.startswith(prefix):
            return cat
    return "general"


class M5ControlResolver:
    name = "m5_control_resolver"
    reads = [
        "analysis.active_asi",
        "analysis.active_threats",
        "analysis.high_risk_domain",
        "inputs.business_context.lifecycle_phases",
    ]
    writes = ["controls.critical_required", "controls.recommended"]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        # ── Sub-path A: critical controls for verdict ──────────────────────────
        # Map ctrl_id → list of ASI-IDs that require it (a control can be required by multiple ASIs)
        critical_map: dict[str, list[str]] = {}

        for asi_id in ctx.analysis.active_asi:
            for ctrl_id in kb.critical_controls_for_asi(asi_id):
                critical_map.setdefault(ctrl_id, [])
                if asi_id not in critical_map[ctrl_id]:
                    critical_map[ctrl_id].append(asi_id)

        # High-risk domain escalation adds CTRL-DEP-05 regardless of active ASIs
        if ctx.analysis.high_risk_domain:
            critical_map.setdefault("CTRL-DEP-05", [])
            if "high_risk_domain" not in critical_map["CTRL-DEP-05"]:
                critical_map["CTRL-DEP-05"].append("high_risk_domain")

        # CTRL-MON-01 (immutable logging) is a universal verdict gate: M7 requires it
        # for APT (plan 7.1.d) and blocks NOT_APT if it is not implemented (7.3.c).
        # Always include it so it reaches the checklist and can be attested, even when
        # no ASI mapping to it is active. If an ASI already required it, keep that trace.
        critical_map.setdefault("CTRL-MON-01", [])
        if not critical_map["CTRL-MON-01"]:
            critical_map["CTRL-MON-01"].append("baseline")

        critical_required: list[CriticalControl] = []
        for ctrl_id, required_by in critical_map.items():
            ctrl = kb.control_by_id(ctrl_id)
            if ctrl is None:
                continue  # selfcheck would have caught this at startup
            critical_required.append(CriticalControl(
                control_id=ctrl_id,
                name=ctrl.name,
                description=ctrl.description,
                required_by_asi=required_by,
                category=_category(ctrl_id),
            ))

        # ── Sub-path B: recommended controls filtered by lifecycle ─────────────
        phases = [p.value for p in ctx.inputs.business_context.lifecycle_phases]

        # Gather candidate controls mitigating any active threat (dedup, keep order)
        seen_ctrl_ids: set[str] = set()
        candidates: list[Control] = []
        for tid in ctx.analysis.active_threats:
            for ctrl in kb.controls_mitigating(tid):
                if ctrl.control_id not in seen_ctrl_ids:
                    seen_ctrl_ids.add(ctrl.control_id)
                    candidates.append(ctrl)

        # Filter by lifecycle via the KB Service (documented API), then enrich
        recommended: list[RecommendedControl] = []
        for ctrl in kb.controls_for_phases(candidates, phases):
            # Only list T-IDs that are actually active (control may mitigate more)
            active_mitigates = [t for t in ctrl.mitigates_threats if t in ctx.analysis.active_threats]
            recommended.append(RecommendedControl(
                control_id=ctrl.control_id,
                name=ctrl.name,
                description=ctrl.description,
                mitigates=active_mitigates,
                lifecycle_phases=ctrl.lifecycle_phases,
            ))

        ctx.controls.critical_required = critical_required
        ctx.controls.recommended = recommended

        return ctx
