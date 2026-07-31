"""End-to-end FULL_VALIDATION flow with manual attestation (Etapa 0).

Exercises the two-phase orchestration (run -> pause -> resume), the orchestrator's
ownership of status transitions, and the report assembly.
"""
from __future__ import annotations

from fixtures.inputs import context, flags

from validation_engine.contracts.assurance import Attestation
from validation_engine.contracts.enums import AttestationStatus, LifecyclePhase, Status, VerdictResult
from validation_engine.modules.reporter import build_report


def _attest_all(ctx, status):
    for c in ctx.controls.critical_required:
        ctx.assurance.attestations[c.control_id] = Attestation(status=status)


def test_run_pauses_at_assurance_and_emits_checklist(orchestrator, kb):
    ctx = context(kb_version=kb.kb_version(), capability_flags=flags(tool_use=True))
    ctx = orchestrator.run(ctx)
    assert ctx.status == Status.AWAITING_ASSURANCE
    assert ctx.controls.critical_required          # M1-M5 ran
    assert ctx.assurance.checklist                 # checklist emitted for attestation
    assert ctx.verdict is None                     # no verdict before assurance (I4)


def test_end_to_end_apt(orchestrator, kb):
    ctx = context(kb_version=kb.kb_version(), capability_flags=flags(tool_use=True),
                  phases=[LifecyclePhase.RUNTIME])
    ctx = orchestrator.run(ctx)

    _attest_all(ctx, AttestationStatus.IMPLEMENTED)
    ctx.assurance.incident_response_plan = True
    ctx.assurance.red_teaming_done = True

    ctx = orchestrator.resume(ctx)
    assert ctx.status == Status.COMPLETED
    assert ctx.verdict.result == VerdictResult.APT

    # Orchestrator owns the status transitions: scoring appears in the history.
    history = [(t.module, t.status.value) for t in ctx.transitions]
    assert ("m7_verdict_engine", "scoring") in history

    report = build_report(ctx)
    assert report["verdict"] == "APT"
    assert report["errors"] == []


def test_end_to_end_not_apt_when_controls_missing(orchestrator, kb):
    ctx = context(kb_version=kb.kb_version(), capability_flags=flags(tool_use=True))
    ctx = orchestrator.run(ctx)

    _attest_all(ctx, AttestationStatus.NOT_IMPLEMENTED)
    ctx.assurance.incident_response_plan = True

    ctx = orchestrator.resume(ctx)
    assert ctx.status == Status.COMPLETED
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_reproducibility_same_inputs_same_analysis(orchestrator, kb):
    # Same (inputs + KB) -> identical analysis/controls layers (I5).
    a = orchestrator.run(context(kb_version=kb.kb_version(), capability_flags=flags(tool_use=True)))
    b = orchestrator.run(context(kb_version=kb.kb_version(), capability_flags=flags(tool_use=True)))
    assert a.analysis.active_asi == b.analysis.active_asi
    assert {c.control_id for c in a.controls.critical_required} == \
           {c.control_id for c in b.controls.critical_required}


def test_m1_error_aborts_and_runs_reporter(orchestrator, kb):
    ctx = context(kb_version=kb.kb_version(), phases=[])  # empty lifecycle -> M1 error
    ctx = orchestrator.run(ctx)
    assert ctx.status == Status.ERROR
    assert any(t.module == "reporter" for t in ctx.transitions)  # Reporter(error)
    report = build_report(ctx)
    assert report["errors"]
