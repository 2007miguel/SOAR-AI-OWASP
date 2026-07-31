"""M5 ControlResolver — critical controls (sub-path A) + recommended (sub-path B)."""
from __future__ import annotations

from fixtures.inputs import context

from validation_engine.modules import M5ControlResolver
from validation_engine.contracts.enums import LifecyclePhase


def _run(kb, active_asi, active_threats=None, high_risk=False, phases=None):
    ctx = context(phases=phases or [LifecyclePhase.RUNTIME])
    ctx.analysis.active_asi = active_asi
    ctx.analysis.active_threats = active_threats or []
    ctx.analysis.high_risk_domain = high_risk
    return M5ControlResolver().run(ctx, kb)


def test_critical_controls_match_kb_for_asi06(kb):
    # ASI06 -> CTRL-DATA-04, CTRL-DATA-05, CTRL-PROMPT-01, CTRL-MON-01 (golden).
    ctx = _run(kb, active_asi=["ASI06"])
    ids = {c.control_id for c in ctx.controls.critical_required}
    assert {"CTRL-DATA-04", "CTRL-DATA-05", "CTRL-PROMPT-01", "CTRL-MON-01"} <= ids


def test_ctrl_mon01_always_present_even_without_mapping_asi(kb):
    # ASI02 does NOT map to CTRL-MON-01, but the universal logging gate must appear.
    ctx = _run(kb, active_asi=["ASI02"])
    mon = [c for c in ctx.controls.critical_required if c.control_id == "CTRL-MON-01"]
    assert mon, "CTRL-MON-01 must always be in the critical set (universal verdict gate)"
    assert mon[0].required_by_asi == ["baseline"]


def test_ctrl_mon01_keeps_asi_trace_when_mapped(kb):
    # When an active ASI already requires it, the ASI trace is kept (not 'baseline').
    ctx = _run(kb, active_asi=["ASI06"])
    mon = next(c for c in ctx.controls.critical_required if c.control_id == "CTRL-MON-01")
    assert "ASI06" in mon.required_by_asi
    assert "baseline" not in mon.required_by_asi


def test_high_risk_domain_adds_ctrl_dep_05(kb):
    ctx = _run(kb, active_asi=["ASI02"], high_risk=True)
    ids = {c.control_id for c in ctx.controls.critical_required}
    assert "CTRL-DEP-05" in ids


def test_every_critical_control_traces_to_a_reason(kb):
    # Invariant I6: each critical control must have a non-empty required_by_asi.
    ctx = _run(kb, active_asi=["ASI06", "ASI08"])
    assert ctx.controls.critical_required
    for c in ctx.controls.critical_required:
        assert c.required_by_asi


def test_recommended_are_filtered_by_lifecycle(kb):
    ctx = _run(kb, active_asi=["ASI02"], active_threats=["T2"], phases=[LifecyclePhase.RUNTIME])
    for c in ctx.controls.recommended:
        assert "runtime" in c.lifecycle_phases
