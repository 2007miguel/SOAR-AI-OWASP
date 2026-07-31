from __future__ import annotations

from .models import KnowledgeBase


class KBSelfCheckError(Exception):
    pass


def run(kb: KnowledgeBase, wizard_flags: set[str] | None = None) -> None:
    """Validate KB internal coherence at startup. Raises KBSelfCheckError if incoherent.

    If wizard_flags is provided, also verifies wizard↔KB flag coverage
    (arquitectura_sistema.txt §8; estructura_engine.txt §2/§3).
    """
    errors: list[str] = []
    errors.extend(_check_activated_risks_cache(kb))
    errors.extend(_check_critical_controls_exist(kb))
    if wizard_flags is not None:
        errors.extend(_check_flag_coverage(kb, wizard_flags))

    if errors:
        detail = "\n".join(f"  - {e}" for e in errors)
        raise KBSelfCheckError(f"KB selfcheck failed ({len(errors)} issue(s)):\n{detail}")


def _check_activated_risks_cache(kb: KnowledgeBase) -> list[str]:
    """Verify that each step's activated_risks matches derivation via threat_catalog.maps_to_asi.
    activated_risks is a cache — any mismatch means the KB is out of sync with Appendix A."""
    threats_by_id = {t.threat_id: t for t in kb.threat_catalog.threats}
    errors: list[str] = []

    for step in kb.capability_taxonomy.steps:
        derived: set[str] = set()
        for tid in step.activated_threats:
            threat = threats_by_id.get(tid)
            if threat:
                derived.update(threat.maps_to_asi)
        cached = set(step.activated_risks)
        if derived != cached:
            errors.append(
                f"{step.step_id}: activated_risks cache {sorted(cached)} "
                f"!= derived from Appendix A {sorted(derived)}"
            )

    return errors


def _check_flag_coverage(kb: KnowledgeBase, wizard_flags: set[str]) -> list[str]:
    """Verify wizard↔KB flag coverage. Every wizard capability_flag must be mapped
    by the KB (in a capability_taxonomy STEP or an operational_capabilities entry),
    and vice versa. A gap means the wizard offers a flag the pipeline would ignore,
    or the KB references a flag the wizard never sets."""
    kb_flags: set[str] = set()
    for step in kb.capability_taxonomy.steps:
        kb_flags.update(step.capability_flags)
    for cap in kb.operational_capabilities.capabilities:
        kb_flags.update(cap.capability_flag_refs)

    errors: list[str] = []
    uncovered = wizard_flags - kb_flags
    if uncovered:
        errors.append(
            f"wizard flags not covered by the KB (no STEP/OC maps them): {sorted(uncovered)}"
        )
    missing = kb_flags - wizard_flags
    if missing:
        errors.append(
            f"KB references capability flags absent from the wizard coverage map: {sorted(missing)}"
        )
    return errors


def _check_critical_controls_exist(kb: KnowledgeBase) -> list[str]:
    """Verify that every CTRL-ID in critical_controls_by_risk exists in controls_catalog."""
    known_ids = {
        ctrl.control_id
        for domain in kb.controls_catalog.domains
        for ctrl in domain.controls
    }
    errors: list[str] = []

    for asi_id, ctrl_ids in kb.verdict_framework.critical_controls_by_risk.items():
        for ctrl_id in ctrl_ids:
            if ctrl_id not in known_ids:
                errors.append(
                    f"critical_controls_by_risk[{asi_id}] references unknown control {ctrl_id}"
                )

    return errors
