from __future__ import annotations

from ..contracts.evidence import AttestationInput
from ..persistence.job_store import JobStore


class AttestationIntake:
    """Merge HITL attestations into the persistent partial state for an assessment."""

    def __init__(self, store: JobStore) -> None:
        self._store = store

    def submit(
        self,
        assessment_id: str,
        attestations: dict[str, AttestationInput],
        incident_response_plan: bool | None = None,
        red_teaming_done: bool | None = None,
        assurance_methods_used: list[str] | None = None,
        red_teaming_critical_findings: bool | None = None,
        supply_chain_unverified: bool | None = None,
        production_access: bool | None = None,
    ) -> bool:
        """Merge attestations into persistent state. Returns True when all required controls are covered."""
        serialized = {k: v.model_dump() for k, v in attestations.items()}

        flags: dict[str, object] = {}
        if incident_response_plan is not None:
            flags["incident_response_plan"] = incident_response_plan
        if red_teaming_done is not None:
            flags["red_teaming_done"] = red_teaming_done
        if red_teaming_critical_findings is not None:
            flags["red_teaming_critical_findings"] = red_teaming_critical_findings
        if supply_chain_unverified is not None:
            flags["supply_chain_unverified"] = supply_chain_unverified
        if production_access is not None:
            flags["production_access"] = production_access
        if assurance_methods_used:
            flags["assurance_methods_used"] = assurance_methods_used

        self._store.update_attestations(assessment_id, serialized, **flags)
        return self._store.is_ready(assessment_id)
