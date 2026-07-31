"""M2 ThreatMapper — golden: capability_flags -> STEPs -> T-IDs.

Golden values are the real OWASP-derived facts from the developed KB.
"""
from __future__ import annotations

from fixtures.inputs import context, flags

from validation_engine.modules import M2ThreatMapper


def _run(kb, **active):
    return M2ThreatMapper().run(context(capability_flags=flags(**active)), kb)


def test_memory_flag_activates_step2(kb):
    # short_term_memory -> STEP-2 -> threats T1, T5
    ctx = _run(kb, short_term_memory=True)
    assert ctx.analysis.active_steps == ["STEP-2"]
    assert ctx.analysis.active_threats == ["T1", "T5"]
    assert ctx.analysis.critical_systems_path is False


def test_tool_flag_activates_step3(kb):
    # tool_use -> STEP-3 -> threats T2, T3, T4, T11, T16, T17
    ctx = _run(kb, tool_use=True)
    assert ctx.analysis.active_steps == ["STEP-3"]
    assert ctx.analysis.active_threats == ["T11", "T16", "T17", "T2", "T3", "T4"]


def test_union_of_flags_accumulates_without_duplicates(kb):
    ctx = _run(kb, short_term_memory=True, tool_use=True)
    assert ctx.analysis.active_steps == ["STEP-2", "STEP-3"]
    assert ctx.analysis.active_threats == ["T1", "T11", "T16", "T17", "T2", "T3", "T4", "T5"]


def test_critical_systems_access_uses_oc_kc66_not_steps(kb):
    # Special path: critical_systems_access is handled via OC-KC6.6 (no STEP).
    ctx = _run(kb, critical_systems_access=True)
    assert ctx.analysis.critical_systems_path is True
    assert ctx.analysis.active_steps == []
    assert ctx.analysis.active_threats == ["T1", "T2", "T3", "T5", "T6", "T7"]
    # every threat is traced to OC-KC6.6, not to a STEP
    assert all("OC-KC6.6" in " ".join(src) for src in ctx.analysis.threat_source_map.values())


def test_no_flags_no_threats(kb):
    ctx = M2ThreatMapper().run(context(), kb)
    assert ctx.analysis.active_steps == []
    assert ctx.analysis.active_threats == []
