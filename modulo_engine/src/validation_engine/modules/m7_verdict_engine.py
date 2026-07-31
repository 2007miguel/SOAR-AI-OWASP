from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.enums import AttestationStatus, VerdictResult
from ..contracts.verdict import VerdictLayer, VerdictTrace
from ..kb.service import KBService


class M7VerdictEngine:
    name = "m7_verdict_engine"
    reads = [
        "controls.critical_required",
        "assurance.attestations",
        "assurance.red_teaming_done",
        "assurance.incident_response_plan",
        "assurance.red_teaming_critical_findings",
        "assurance.supply_chain_unverified",
        "assurance.production_access",
        "analysis.high_risk_domain",
    ]
    # Per the read/write matrix (assessment_context.txt §3), M7 writes only verdict.*.
    # Status transitions (scoring → completed) are owned by the orchestrator.
    writes = ["verdict"]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        high_severity = set(kb.high_severity_risks())

        def ctrl_status(ctrl_id: str) -> str:
            att = ctx.assurance.attestations.get(ctrl_id)
            return att.status.value if att else AttestationStatus.NOT_IMPLEMENTED.value

        # IDs of critical controls required by high-severity ASIs
        high_severity_ctrl_ids = {
            ctrl.control_id
            for ctrl in ctx.controls.critical_required
            if any(asi in high_severity for asi in ctrl.required_by_asi)
        }

        # Active high-severity ASIs (determines if red teaming is mandatory)
        active_high_severity_asi = {
            asi
            for ctrl in ctx.controls.critical_required
            for asi in ctrl.required_by_asi
            if asi in high_severity
        }

        # ── Evaluate NOT_APT first (blocking conditions) ───────────────────────
        not_apt_reasons: list[str] = []

        # a) Critical control of a high-severity ASI not implemented
        for ctrl_id in high_severity_ctrl_ids:
            if ctrl_status(ctrl_id) == AttestationStatus.NOT_IMPLEMENTED.value:
                not_apt_reasons.append(
                    f"{ctrl_id} (required by high-severity ASI) is not implemented"
                )

        # b) No incident response plan
        if not ctx.assurance.incident_response_plan:
            not_apt_reasons.append("Incident response plan is not defined")

        # c) CTRL-MON-01 (immutable logging) not implemented — no traceability
        if ctrl_status("CTRL-MON-01") == AttestationStatus.NOT_IMPLEMENTED.value:
            not_apt_reasons.append("CTRL-MON-01 (immutable logging) is not implemented")

        # d) Supply-chain components unverified while the agent has production access
        if ctx.assurance.supply_chain_unverified and ctx.assurance.production_access:
            not_apt_reasons.append(
                "Supply-chain components are unverified and the agent has direct production access"
            )

        # e) Red teaming reported unmitigated critical findings
        if ctx.assurance.red_teaming_done and ctx.assurance.red_teaming_critical_findings:
            not_apt_reasons.append(
                "Red teaming reported unmitigated critical vulnerabilities"
            )

        if not_apt_reasons:
            ctx.verdict = VerdictLayer(
                result=VerdictResult.NOT_APT,
                label="Not Apt for Production",
                rationale="One or more critical blocking conditions are not satisfied.",
                blocking_reasons=not_apt_reasons,
                trace=_build_trace(ctx),
            )
            return ctx

        # ── Evaluate APT (all positive conditions) ────────────────────────────
        all_critical_implemented = all(
            ctrl_status(c.control_id) == AttestationStatus.IMPLEMENTED.value
            for c in ctx.controls.critical_required
        )
        red_teaming_ok = (not active_high_severity_asi) or ctx.assurance.red_teaming_done
        hotl_ok = (not ctx.analysis.high_risk_domain) or (
            ctrl_status("CTRL-DEP-05") == AttestationStatus.IMPLEMENTED.value
        )

        if all_critical_implemented and red_teaming_ok and hotl_ok:
            ctx.verdict = VerdictLayer(
                result=VerdictResult.APT,
                label="Apt for Production",
                rationale=(
                    "All critical controls are implemented. "
                    "Red teaming and incident response requirements are satisfied."
                ),
                blocking_reasons=[],
                trace=_build_trace(ctx),
            )
            return ctx

        # ── APT_WITH_RESTRICTIONS (intermediate case) ─────────────────────────
        restrictions: list[str] = []

        if not all_critical_implemented:
            pending = [
                c.control_id for c in ctx.controls.critical_required
                if ctrl_status(c.control_id) != AttestationStatus.IMPLEMENTED.value
            ]
            restrictions.append(f"Pending critical controls: {', '.join(pending)}")

        if not red_teaming_ok:
            asi_list = ", ".join(sorted(active_high_severity_asi))
            restrictions.append(
                f"Red teaming not completed for high-severity risks: {asi_list}"
            )

        if not hotl_ok:
            restrictions.append(
                "Human-Over-The-Loop (CTRL-DEP-05) not fully implemented for high-risk domain"
            )

        ctx.verdict = VerdictLayer(
            result=VerdictResult.APT_WITH_RESTRICTIONS,
            label="Apt for Production with Restrictions",
            rationale="Core controls are in place but some conditions remain pending.",
            blocking_reasons=restrictions,
            trace=_build_trace(ctx),
        )
        return ctx


def _build_trace(ctx: AssessmentContext) -> VerdictTrace:
    # flags_to_threats: flag → [T-IDs]
    # Derived by inverting threat_source_map (T-ID → ["STEP[flag]" | "OC-KC6.6[flag]"])
    flags_to_threats: dict[str, list[str]] = {}
    for tid, sources in ctx.analysis.threat_source_map.items():
        for source in sources:
            flag = source.split("[")[1].rstrip("]") if "[" in source else source
            flags_to_threats.setdefault(flag, [])
            if tid not in flags_to_threats[flag]:
                flags_to_threats[flag].append(tid)

    # threats_to_risks: T-ID → [ASI-IDs]
    # Derived by inverting asi_trace (ASI-ID → [T-IDs])
    threats_to_risks: dict[str, list[str]] = {}
    for asi_id, tids in ctx.analysis.asi_trace.items():
        for tid in tids:
            threats_to_risks.setdefault(tid, [])
            if asi_id not in threats_to_risks[tid]:
                threats_to_risks[tid].append(asi_id)

    # risks_to_controls: ASI-ID → [CTRL-IDs]
    risks_to_controls: dict[str, list[str]] = {}
    for ctrl in ctx.controls.critical_required:
        for asi_id in ctrl.required_by_asi:
            risks_to_controls.setdefault(asi_id, [])
            if ctrl.control_id not in risks_to_controls[asi_id]:
                risks_to_controls[asi_id].append(ctrl.control_id)

    return VerdictTrace(
        flags_to_threats=flags_to_threats,
        threats_to_risks=threats_to_risks,
        risks_to_controls=risks_to_controls,
    )
