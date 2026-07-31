from __future__ import annotations

from pydantic import BaseModel

from ..contracts.inputs import Aibom, BusinessContext, CapabilityFlags
from ..contracts.enums import AttestationStatus


# ── Request DTOs ──────────────────────────────────────────────────────────────

class StartAssessmentRequest(BaseModel):
    capability_flags: CapabilityFlags
    business_context: BusinessContext
    aibom: Aibom | None = None


class AttestationInput(BaseModel):
    status: AttestationStatus
    evidence: str | None = None
    assurance_method: str | None = None


class AttestRequest(BaseModel):
    attestations: dict[str, AttestationInput] = {}
    incident_response_plan: bool | None = None   # None = leave unchanged
    red_teaming_done: bool | None = None          # None = leave unchanged
    assurance_methods_used: list[str] = []
    # Optional verdict signals (plan 7.3.d/7.3.e). None = leave unchanged.
    red_teaming_critical_findings: bool | None = None
    supply_chain_unverified: bool | None = None
    production_access: bool | None = None


# ── Response DTOs ─────────────────────────────────────────────────────────────

class ChecklistItemOut(BaseModel):
    control_id: str
    why: list[str]
    category: str
    suggested_assur: list[str]


class StartAssessmentResponse(BaseModel):
    assessment_id: str
    status: str
    checklist: list[ChecklistItemOut]
    warnings: list[dict] = []   # {code, message} — as produced by M1
    errors: list[dict] = []     # {code, message} — blocking; present when status == "error"


class AttestResponse(BaseModel):
    assessment_id: str
    status: str
    is_ready: bool


class AssessmentStatusResponse(BaseModel):
    assessment_id: str
    kb_version: str
    status: str
    report: dict | None = None
