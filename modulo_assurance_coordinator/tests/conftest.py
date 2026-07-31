from __future__ import annotations

from datetime import datetime, timezone

import pytest

from assurance_coordinator.persistence.job_store import SessionData


class FakeStore:
    """In-memory stand-in for JobStore.

    Mirrors the interface used by AttestationIntake / PartialStore so the
    HITL logic can be tested without a live PostgreSQL/JSONB backend.
    """

    def __init__(self) -> None:
        self.sessions: dict[str, SessionData] = {}

    def create_session(self, assessment_id, active_asi, checklist) -> None:
        now = datetime.now(timezone.utc)
        self.sessions[assessment_id] = SessionData(
            assessment_id=assessment_id,
            active_asi=list(active_asi),
            checklist=list(checklist),
            attestations={},
            incident_response_plan=False,
            red_teaming_done=False,
            red_teaming_critical_findings=False,
            supply_chain_unverified=False,
            production_access=False,
            assurance_methods_used=[],
            status="pending",
            created_at=now,
            updated_at=now,
        )

    def get_session(self, assessment_id) -> SessionData | None:
        return self.sessions.get(assessment_id)

    def update_attestations(self, assessment_id, new_attestations, **flags) -> None:
        s = self.sessions.get(assessment_id)
        if s is None:
            raise KeyError(assessment_id)
        s.attestations = {**s.attestations, **new_attestations}
        for key, val in flags.items():
            if val is None:
                continue
            if key == "assurance_methods_used":
                s.assurance_methods_used = sorted(
                    set(s.assurance_methods_used) | set(val)
                )
            elif hasattr(s, key):
                setattr(s, key, val)

    def is_ready(self, assessment_id) -> bool:
        s = self.sessions.get(assessment_id)
        if s is None:
            return False
        critical = {item["control_id"] for item in s.checklist}
        return critical.issubset(set(s.attestations.keys()))

    def mark_ready(self, assessment_id) -> None:
        self.sessions[assessment_id].status = "ready"


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()
