"""KB integrity golden tests: the real KB must be internally coherent with OWASP.

These lock the invariants the engine relies on at startup (arquitectura_sistema.txt
Sección 8; estructura_engine.txt §2/§3).
"""
from __future__ import annotations

import pytest

from validation_engine.kb import KBSelfCheckError, selfcheck


def test_real_kb_passes_selfcheck(raw_kb, wizard_flags):
    # Full startup selfcheck against the real KB + wizard must not raise.
    selfcheck(raw_kb, wizard_flags)


def test_activated_risks_match_appendix_a(raw_kb):
    # For every STEP, the activated_risks cache must equal the derivation via
    # threat_catalog.maps_to_asi (Appendix A). This is the OWASP fidelity anchor.
    threats = {t.threat_id: t for t in raw_kb.threat_catalog.threats}
    for step in raw_kb.capability_taxonomy.steps:
        derived: set[str] = set()
        for tid in step.activated_threats:
            derived.update(threats[tid].maps_to_asi)
        assert set(step.activated_risks) == derived, f"{step.step_id}: cache != Appendix A"


def test_critical_controls_have_no_orphans(raw_kb):
    known = {c.control_id for d in raw_kb.controls_catalog.domains for c in d.controls}
    for asi, ids in raw_kb.verdict_framework.critical_controls_by_risk.items():
        for cid in ids:
            assert cid in known, f"{cid} referenced by {asi} does not exist in controls_catalog"


def test_t9_maps_to_no_asi(raw_kb):
    # T9 (Identity Spoofing) has maps_to_asi == [] in Appendix A — faithful to OWASP.
    t9 = next(t for t in raw_kb.threat_catalog.threats if t.threat_id == "T9")
    assert t9.maps_to_asi == []


def test_flag_coverage_gap_fails_selfcheck(raw_kb, wizard_flags):
    # A wizard flag with no KB coverage must fail the startup selfcheck.
    with pytest.raises(KBSelfCheckError):
        selfcheck(raw_kb, wizard_flags | {"__flag_not_in_kb__"})
