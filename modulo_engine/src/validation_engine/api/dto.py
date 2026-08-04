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


class ToolResultIn(BaseModel):
    connector: str
    control_id: str | None = None
    asi: str | None = None
    verdict: str
    findings: list[dict] = []
    raw_ref: str | None = None


class EvidenceBundleIn(BaseModel):
    """Body sent by the coordinator's resume callback. Populates ctx.assurance before M7."""
    assessment_id: str
    attestations: dict[str, AttestationInput]
    tool_results: list[ToolResultIn] = []
    red_teaming_done: bool = False
    incident_response_plan: bool = False
    assurance_methods_used: list[str] = []
    red_teaming_critical_findings: bool = False
    supply_chain_unverified: bool = False
    production_access: bool = False


# ── Response DTOs ─────────────────────────────────────────────────────────────

class AsiDetail(BaseModel):
    asi_id: str
    name: str
    scope: str | None = None
    llm_top10_mapping: list[str] = []
    aivss_core_risk: str | None = None


class ThreatDetail(BaseModel):
    threat_id: str
    name: str
    description: str | None = None


class AssurMethodDetail(BaseModel):
    method_id: str
    name: str
    description: str | None = None
    tools: list[dict] = []


class ChecklistItemOut(BaseModel):
    control_id: str
    control_name: str = ""
    control_description: str = ""
    why: list[str]                              # ASI-IDs that require this control
    why_detail: list[AsiDetail] = []            # enriched ASI info
    threats: list[str]                          # T-IDs that activate those ASIs
    threats_detail: list[ThreatDetail] = []     # enriched threat info
    category: str
    suggested_assur: list[str]
    suggested_assur_detail: list[AssurMethodDetail] = []  # enriched assurance info


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
