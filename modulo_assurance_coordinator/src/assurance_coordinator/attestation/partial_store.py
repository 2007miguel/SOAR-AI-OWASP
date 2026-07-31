from __future__ import annotations

from ..contracts.evidence import AttestationInput, EvidenceBundle
from ..persistence.job_store import JobStore, SessionData


class PartialStore:
    """Read-side view of partial attestation state for a coordinator session.

    Provides domain-level queries over the raw SessionData rows without
    exposing SQLAlchemy internals to the rest of the package.
    """

    def __init__(self, store: JobStore) -> None:
        self._store = store

    def get_pending(self, assessment_id: str) -> list[str]:
        """Return control_ids that still have no attestation."""
        data: SessionData | None = self._store.get_session(assessment_id)
        if data is None:
            return []
        all_ids = {item["control_id"] for item in data.checklist}
        return sorted(all_ids - set(data.attestations.keys()))

    def build_bundle(self, assessment_id: str) -> EvidenceBundle | None:
        """Build a full EvidenceBundle from whatever partial state exists."""
        data = self._store.get_session(assessment_id)
        if data is None:
            return None
        return EvidenceBundle(
            assessment_id=assessment_id,
            attestations={
                k: AttestationInput(**v) for k, v in data.attestations.items()
            },
            red_teaming_done=data.red_teaming_done,
            incident_response_plan=data.incident_response_plan,
            assurance_methods_used=data.assurance_methods_used,
            red_teaming_critical_findings=data.red_teaming_critical_findings,
            supply_chain_unverified=data.supply_chain_unverified,
            production_access=data.production_access,
        )
