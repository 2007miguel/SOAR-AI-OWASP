from __future__ import annotations

from .models import Control, KnowledgeBase, OperationalCapability


class KBService:
    """Read-only query interface over the knowledge base. Modules must use this
    instead of navigating the JSON directly."""

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb
        # Build lookup indexes at construction time to keep queries O(1) / O(n) simple
        self._threats_by_id = {t.threat_id: t for t in kb.threat_catalog.threats}
        self._steps_by_id = {s.step_id: s for s in kb.capability_taxonomy.steps}
        self._all_controls: list[Control] = [
            ctrl
            for domain in kb.controls_catalog.domains
            for ctrl in domain.controls
        ]

    # ── Capability taxonomy ────────────────────────────────────────────────────

    def steps_for_flag(self, flag: str) -> list[str]:
        """Return step_ids whose capability_flags list contains the given flag."""
        return [
            step.step_id
            for step in self._kb.capability_taxonomy.steps
            if flag in step.capability_flags
        ]

    def threats_for_step(self, step_id: str) -> list[str]:
        """Return activated_threats for a step."""
        step = self._steps_by_id.get(step_id)
        return step.activated_threats if step else []

    # ── Threat → ASI (Appendix A) ─────────────────────────────────────────────

    def maps_to_asi(self, threat_id: str) -> list[str]:
        """Return ASI-IDs mapped by this threat (via Appendix A). T9 returns []."""
        entry = self._threats_by_id.get(threat_id)
        return entry.maps_to_asi if entry else []

    # ── Operational capabilities ───────────────────────────────────────────────

    def oc_for_flag(self, flag: str) -> OperationalCapability | None:
        """Return the OperationalCapability that references this flag. Used for the
        critical_systems_access special path (OC-KC6.6)."""
        for cap in self._kb.operational_capabilities.capabilities:
            if flag in cap.capability_flag_refs:
                return cap
        return None

    # ── Controls ───────────────────────────────────────────────────────────────

    def critical_controls_for_asi(self, asi_id: str) -> list[str]:
        """Return CTRL-IDs required by this ASI per verdict_framework."""
        return self._kb.verdict_framework.critical_controls_by_risk.get(asi_id, [])

    def controls_mitigating(self, threat_id: str) -> list[Control]:
        """Return all controls that list this T-ID in mitigates_threats."""
        return [c for c in self._all_controls if threat_id in c.mitigates_threats]

    def controls_for_phases(self, controls: list[Control], phases: list[str]) -> list[Control]:
        """Filter controls to those applicable to at least one of the given lifecycle phases."""
        phase_set = set(phases)
        return [c for c in controls if set(c.lifecycle_phases) & phase_set]

    def control_by_id(self, control_id: str) -> Control | None:
        """Look up a control by its CTRL-ID."""
        return next((c for c in self._all_controls if c.control_id == control_id), None)

    # ── Verdict framework ──────────────────────────────────────────────────────

    def high_risk_domains(self) -> list[str]:
        """Business domains that require high-risk escalation (EU AI Act)."""
        return self._kb.verdict_framework.high_risk_business_domains.domains

    def high_severity_risks(self) -> list[str]:
        """ASI-IDs whose missing critical control yields NOT_APT."""
        return self._kb.verdict_framework.high_severity_risks.risks

    # ── Architecture ───────────────────────────────────────────────────────────

    def architecture_recommendations(self, arch_id: str) -> dict:
        """Return security_practices and priority_control_domains for an arch pattern.
        Always includes ARCH-CROSS as baseline."""
        result: dict = {"security_practices": [], "priority_control_domains": []}
        for arch in self._kb.architecture_types.types:
            if arch.arch_id in (arch_id, "ARCH-CROSS"):
                result["security_practices"].extend(arch.security_practices)
                result["priority_control_domains"].extend(arch.priority_control_domains)
        return result

    # ── Assurance methods ──────────────────────────────────────────────────────

    def assurance_methods_for_asi(self, asi_id: str) -> list[str]:
        """Return ASSUR-IDs whose covers_risks includes this ASI."""
        return [
            m.method_id
            for m in self._kb.assurance_methods.methods
            if asi_id in m.covers_risks
        ]

    # ── Meta ───────────────────────────────────────────────────────────────────

    def kb_version(self) -> str:
        return self._kb.metadata.version
