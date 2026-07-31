"""M7 VerdictEngine — the decision layer (APT / APT_WITH_RESTRICTIONS / NOT_APT).

M7 reads high_severity_risks from the real KB (ASI01/02/03/05/06). It writes only
the verdict; the status is owned by the orchestrator.
"""
from __future__ import annotations

from fixtures.inputs import context

from validation_engine.modules import M7VerdictEngine
from validation_engine.contracts.controls import CriticalControl
from validation_engine.contracts.assurance import Attestation
from validation_engine.contracts.enums import AttestationStatus, Status, VerdictResult

IMPL = AttestationStatus.IMPLEMENTED
NOT = AttestationStatus.NOT_IMPLEMENTED
PARTIAL = AttestationStatus.PARTIAL


def _critical(control_id: str, asis: list[str]) -> CriticalControl:
    return CriticalControl(control_id=control_id, name=control_id, description="", required_by_asi=asis, category="x")


def _verdict(kb, controls, attest, ir=True, rt=True, high_risk=False, **assur):
    ctx = context()
    ctx.controls.critical_required = controls
    for cid, st in attest.items():
        ctx.assurance.attestations[cid] = Attestation(status=st)
    ctx.assurance.incident_response_plan = ir
    ctx.assurance.red_teaming_done = rt
    ctx.analysis.high_risk_domain = high_risk
    for key, val in assur.items():
        setattr(ctx.assurance, key, val)
    return M7VerdictEngine().run(ctx, kb)


def test_apt_when_all_implemented(kb):
    controls = [_critical("CTRL-MON-01", ["ASI06"]), _critical("CTRL-PROMPT-01", ["ASI06"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL, "CTRL-PROMPT-01": IMPL})
    assert ctx.verdict.result == VerdictResult.APT


def test_not_apt_when_high_severity_control_missing(kb):
    # ASI06 is high-severity; a missing critical control -> NOT_APT.
    controls = [_critical("CTRL-MON-01", ["ASI06"]), _critical("CTRL-PROMPT-01", ["ASI06"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL, "CTRL-PROMPT-01": NOT})
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_not_apt_without_immutable_logging(kb):
    controls = [_critical("CTRL-MON-01", ["baseline"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": NOT})
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_not_apt_without_incident_response_plan(kb):
    controls = [_critical("CTRL-MON-01", ["baseline"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL}, ir=False)
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_not_apt_supply_chain_unverified_with_production_access(kb):
    controls = [_critical("CTRL-MON-01", ["baseline"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL}, supply_chain_unverified=True, production_access=True)
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_not_apt_red_teaming_critical_findings(kb):
    controls = [_critical("CTRL-MON-01", ["baseline"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL}, red_teaming_critical_findings=True)
    assert ctx.verdict.result == VerdictResult.NOT_APT


def test_apt_with_restrictions_on_partial_non_high_severity(kb):
    # ASI07 is not high-severity; a partial control there -> not NOT_APT, not full APT.
    controls = [_critical("CTRL-MON-01", ["baseline"]), _critical("CTRL-INTERAGENT-01", ["ASI07"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL, "CTRL-INTERAGENT-01": PARTIAL})
    assert ctx.verdict.result == VerdictResult.APT_WITH_RESTRICTIONS


def test_m7_writes_verdict_but_not_status(kb):
    # Read/write matrix: M7 writes verdict.*, the orchestrator owns status.
    controls = [_critical("CTRL-MON-01", ["baseline"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL})
    assert ctx.verdict is not None
    assert ctx.status == Status.INTAKE  # unchanged by M7


def test_verdict_trace_is_populated(kb):
    controls = [_critical("CTRL-MON-01", ["ASI06"])]
    ctx = _verdict(kb, controls, {"CTRL-MON-01": IMPL})
    assert ctx.verdict.trace.risks_to_controls.get("ASI06") == ["CTRL-MON-01"]
