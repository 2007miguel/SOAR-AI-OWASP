from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class AttestationStatus(str, Enum):
    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    NOT_IMPLEMENTED = "not_implemented"


class AttestationInput(BaseModel):
    status: AttestationStatus
    evidence: str | None = None
    assurance_method: str | None = None


class ToolResult(BaseModel):
    connector: str
    control_id: str | None = None
    asi: str | None = None
    verdict: str
    findings: list[dict] = []
    raw_ref: str | None = None


class EvidenceBundle(BaseModel):
    assessment_id: str
    attestations: dict[str, AttestationInput]   # control_id → attestation
    tool_results: list[ToolResult] = []
    red_teaming_done: bool = False
    incident_response_plan: bool = False
    assurance_methods_used: list[str] = []

    # Optional verdict signals consumed by the engine's M7 (aligned with the
    # engine's AssuranceLayer). Default False → no trigger unless the evaluator
    # reports the data via HITL. Full aibom exploitation deferred to v2.
    red_teaming_critical_findings: bool = False  # unmitigated critical findings from red teaming
    supply_chain_unverified: bool = False        # supply-chain components not verified
    production_access: bool = False              # agent has direct production access
