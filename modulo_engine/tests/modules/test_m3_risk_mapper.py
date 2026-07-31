"""M3 RiskMapper — golden: set of flags -> set of ASI (via Appendix A).

The single most important fidelity test: locks the flags -> ASI mapping to the
developed OWASP KB. Derivation path is always flags -> STEP -> T-IDs -> ASI.
"""
from __future__ import annotations

from fixtures.inputs import context, flags

from validation_engine.modules import M2ThreatMapper, M3RiskMapper


def _flags_to_asi(kb, **active):
    ctx = context(capability_flags=flags(**active))
    ctx = M2ThreatMapper().run(ctx, kb)
    ctx = M3RiskMapper().run(ctx, kb)
    return ctx


def test_golden_memory_flag_to_asi(kb):
    ctx = _flags_to_asi(kb, short_term_memory=True)
    assert ctx.analysis.active_asi == ["ASI06", "ASI08"]


def test_golden_tool_flag_to_asi(kb):
    ctx = _flags_to_asi(kb, tool_use=True)
    assert ctx.analysis.active_asi == ["ASI02", "ASI03", "ASI04", "ASI05", "ASI06", "ASI07"]


def test_golden_union_to_asi(kb):
    ctx = _flags_to_asi(kb, short_term_memory=True, tool_use=True)
    assert ctx.analysis.active_asi == [
        "ASI02", "ASI03", "ASI04", "ASI05", "ASI06", "ASI07", "ASI08",
    ]


def test_asi_trace_backlinks_to_active_threats(kb):
    ctx = _flags_to_asi(kb, short_term_memory=True)
    assert ctx.analysis.asi_trace  # non-empty
    for asi, tids in ctx.analysis.asi_trace.items():
        assert tids, f"{asi} has no threat trace"
        assert all(t in ctx.analysis.active_threats for t in tids)


def test_no_threats_no_asi(kb):
    ctx = _flags_to_asi(kb)
    assert ctx.analysis.active_asi == []
