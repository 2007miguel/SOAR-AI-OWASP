from __future__ import annotations

from pydantic import BaseModel

from .enums import AttestationStatus


class ChecklistItem(BaseModel):
    control_id: str
    why: list[str]                  # ASI-IDs that require this control
    category: str
    suggested_assur: list[str]      # ASSUR-IDs recommended
    status: AttestationStatus = AttestationStatus.NOT_IMPLEMENTED
    evidence: str | None = None


class Attestation(BaseModel):
    status: AttestationStatus
    evidence: str | None = None
    assurance_method: str | None = None  # ASSUR-ID used


class ToolResult(BaseModel):
    connector: str
    control_id: str | None = None
    asi: str | None = None
    verdict: str
    findings: list[dict] = []
    raw_ref: str | None = None


class AssuranceLayer(BaseModel):
    checklist: list[ChecklistItem] = []
    attestations: dict[str, Attestation] = {}   # control_id → Attestation
    tool_results: list[ToolResult] = []
    red_teaming_done: bool = False
    incident_response_plan: bool = False
    assurance_methods_used: list[str] = []      # ASSUR-IDs executed

    # Optional verdict signals (plan 7.3.d/7.3.e). Default False → no trigger
    # unless the evaluator reports the data. Full aibom exploitation deferred to v2.
    red_teaming_critical_findings: bool = False  # unmitigated critical findings from red teaming
    supply_chain_unverified: bool = False        # supply-chain components not verified
    production_access: bool = False              # agent has direct production access
