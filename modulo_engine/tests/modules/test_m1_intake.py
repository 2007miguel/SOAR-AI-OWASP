"""M1 Intake & Validation — per-request input validation (not OWASP taxonomy)."""
from __future__ import annotations

from fixtures.inputs import context, flags

from validation_engine.modules import M1IntakeValidation
from validation_engine.contracts.enums import ArchitectureId, Status


def test_valid_inputs_pass(kb):
    ctx = context(capability_flags=flags(tool_use=True), aibom=None)
    ctx = M1IntakeValidation().run(ctx, kb)
    assert ctx.status == Status.ANALYZING
    assert ctx.analysis.validation.ok is True
    assert ctx.analysis.validation.errors == []


def test_empty_lifecycle_is_blocking_error(kb):
    ctx = context(phases=[])
    ctx = M1IntakeValidation().run(ctx, kb)
    assert ctx.status == Status.ERROR
    assert ctx.analysis.validation.ok is False
    assert any(e["code"] == "LIFECYCLE_PHASES_EMPTY" for e in ctx.analysis.validation.errors)


def test_arch_flag_mismatch_is_non_blocking_warning(kb):
    # ARCH-CENTRAL but multi_agent_architecture=False -> warning, not error.
    ctx = context(arch=ArchitectureId.CENTRAL, capability_flags=flags(multi_agent_architecture=False))
    ctx = M1IntakeValidation().run(ctx, kb)
    assert ctx.status == Status.ANALYZING
    assert any(w["code"] == "ARCH_FLAG_MISMATCH" for w in ctx.analysis.warnings)


def test_missing_aibom_warns(kb):
    ctx = context(aibom=None)
    ctx = M1IntakeValidation().run(ctx, kb)
    assert any(w["code"] == "AIBOM_ABSENT" for w in ctx.analysis.warnings)
