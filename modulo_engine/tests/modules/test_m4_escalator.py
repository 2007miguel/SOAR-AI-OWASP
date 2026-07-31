"""M4 ContextEscalator — business/architecture context (never alters the ASI set)."""
from __future__ import annotations

from fixtures.inputs import context

from validation_engine.modules import M4ContextEscalator
from validation_engine.contracts.enums import ArchitectureId, BusinessDomain


def test_high_risk_domain_escalates(kb):
    # Finance is a high-risk domain (EU AI Act) -> escalation + HOTL.
    ctx = context(domain=BusinessDomain.FINANCE)
    ctx = M4ContextEscalator().run(ctx, kb)
    assert ctx.analysis.high_risk_domain is True
    assert ctx.analysis.hotl_required is True
    assert ctx.analysis.escalations  # non-empty


def test_non_high_risk_domain_no_escalation(kb):
    # Retail is not a high-risk domain.
    ctx = context(domain=BusinessDomain.RETAIL)
    ctx = M4ContextEscalator().run(ctx, kb)
    assert ctx.analysis.high_risk_domain is False
    assert ctx.analysis.hotl_required is False
    assert ctx.analysis.escalations == []


def test_architecture_does_not_change_asi(kb):
    # Invariant I3: architecture only yields recommendations, never ASI.
    ctx = context(arch=ArchitectureId.SWARM)
    ctx.analysis.active_asi = ["ASI02", "ASI06"]
    ctx = M4ContextEscalator().run(ctx, kb)
    assert ctx.analysis.active_asi == ["ASI02", "ASI06"]
    assert ctx.analysis.architecture_recos is not None
