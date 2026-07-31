from __future__ import annotations

from assurance_coordinator.attestation.intake import AttestationIntake
from assurance_coordinator.attestation.partial_store import PartialStore
from assurance_coordinator.contracts.evidence import AttestationInput, AttestationStatus


CHECKLIST = [
    {"control_id": "CTRL-PROMPT-01", "why": ["ASI01"], "category": "herramienta_tecnica", "suggested_assur": ["ASSUR-01"]},
    {"control_id": "CTRL-MON-01", "why": ["ASI01"], "category": "revision_config", "suggested_assur": []},
]


def _seed(store):
    store.create_session("A1", ["ASI01"], CHECKLIST)


def test_partial_attestation_is_not_ready(store):
    _seed(store)
    intake = AttestationIntake(store)
    ready = intake.submit(
        "A1",
        {"CTRL-PROMPT-01": AttestationInput(status=AttestationStatus.IMPLEMENTED, evidence="ok")},
        incident_response_plan=True,
    )
    assert ready is False
    assert PartialStore(store).get_pending("A1") == ["CTRL-MON-01"]
    assert store.get_session("A1").incident_response_plan is True


def test_complete_attestation_becomes_ready(store):
    _seed(store)
    intake = AttestationIntake(store)
    intake.submit("A1", {"CTRL-PROMPT-01": AttestationInput(status=AttestationStatus.IMPLEMENTED)})
    ready = intake.submit("A1", {"CTRL-MON-01": AttestationInput(status=AttestationStatus.PARTIAL)})
    assert ready is True
    assert PartialStore(store).get_pending("A1") == []


def test_verdict_signal_flags_are_persisted(store):
    """The three M7 signals must merge through intake into persistent state."""
    _seed(store)
    intake = AttestationIntake(store)
    intake.submit(
        "A1",
        {
            "CTRL-PROMPT-01": AttestationInput(status=AttestationStatus.IMPLEMENTED),
            "CTRL-MON-01": AttestationInput(status=AttestationStatus.IMPLEMENTED),
        },
        red_teaming_done=True,
        red_teaming_critical_findings=True,
        supply_chain_unverified=True,
        production_access=True,
        assurance_methods_used=["ASSUR-01"],
    )
    session = store.get_session("A1")
    assert session.red_teaming_critical_findings is True
    assert session.supply_chain_unverified is True
    assert session.production_access is True

    bundle = PartialStore(store).build_bundle("A1")
    assert bundle.red_teaming_critical_findings is True
    assert bundle.supply_chain_unverified is True
    assert bundle.production_access is True
    assert bundle.assurance_methods_used == ["ASSUR-01"]


def test_none_flags_leave_state_unchanged(store):
    """Passing None for a flag must not overwrite a previously-set value."""
    _seed(store)
    intake = AttestationIntake(store)
    intake.submit("A1", {}, production_access=True)
    intake.submit("A1", {"CTRL-PROMPT-01": AttestationInput(status=AttestationStatus.IMPLEMENTED)})
    assert store.get_session("A1").production_access is True
