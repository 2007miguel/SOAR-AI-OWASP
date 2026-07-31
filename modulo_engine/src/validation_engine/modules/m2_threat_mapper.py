from __future__ import annotations

from ..contracts import AssessmentContext
from ..kb.service import KBService


class M2ThreatMapper:
    name = "m2_threat_mapper"
    reads = ["inputs.capability_flags"]
    writes = [
        "analysis.active_steps",
        "analysis.active_threats",
        "analysis.threat_source_map",
        "analysis.critical_systems_path",
    ]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        active_steps: set[str] = set()
        active_threats: set[str] = set()
        threat_source_map: dict[str, list[str]] = {}
        critical_systems_path = False

        active_flags = ctx.inputs.capability_flags.active()

        for flag in active_flags:
            # Special path: critical_systems_access is handled via OC-KC6.6,
            # not via capability_taxonomy (it has no STEP mapping).
            if flag == "critical_systems_access":
                oc = kb.oc_for_flag(flag)
                if oc:
                    for tid in oc.core_threats:
                        active_threats.add(tid)
                        threat_source_map.setdefault(tid, [])
                        source = f"OC-KC6.6[{flag}]"
                        if source not in threat_source_map[tid]:
                            threat_source_map[tid].append(source)
                    critical_systems_path = True
                continue

            for step_id in kb.steps_for_flag(flag):
                active_steps.add(step_id)
                for tid in kb.threats_for_step(step_id):
                    active_threats.add(tid)
                    threat_source_map.setdefault(tid, [])
                    source = f"{step_id}[{flag}]"
                    if source not in threat_source_map[tid]:
                        threat_source_map[tid].append(source)

        ctx.analysis.active_steps = sorted(active_steps)
        ctx.analysis.active_threats = sorted(active_threats)
        ctx.analysis.threat_source_map = threat_source_map
        ctx.analysis.critical_systems_path = critical_systems_path

        return ctx
