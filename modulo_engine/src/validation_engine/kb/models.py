from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CapabilityStep(BaseModel):
    step_id: str
    capability_flags: list[str]
    activated_threats: list[str]
    activated_risks: list[str] = []  # cache — not used as source; validated by selfcheck


class CapabilityTaxonomy(BaseModel):
    steps: list[CapabilityStep]


class ThreatEntry(BaseModel):
    threat_id: str
    name: str
    maps_to_asi: list[str]  # Appendix A — source of truth for T-ID → ASI


class ThreatCatalog(BaseModel):
    threats: list[ThreatEntry]


class Control(BaseModel):
    control_id: str
    name: str
    description: str
    mitigates_threats: list[str] = []
    lifecycle_phases: list[str] = []  # injected from parent domain by loader


class ControlDomain(BaseModel):
    domain_id: str
    applicable_lifecycle_phases: list[str] = []
    controls: list[Control]


class ControlsCatalog(BaseModel):
    domains: list[ControlDomain]


class AssuranceMethod(BaseModel):
    method_id: str
    covers_risks: list[str]


class AssuranceMethods(BaseModel):
    methods: list[AssuranceMethod]


class ArchitectureType(BaseModel):
    arch_id: str
    security_practices: list[dict] = []
    priority_control_domains: list[str] = []


class ArchitectureTypes(BaseModel):
    types: list[ArchitectureType]


class OperationalCapability(BaseModel):
    capability_id: str
    capability_flag_refs: list[str]
    core_threats: list[str]
    controls: list[dict] = []
    special_note: str | None = None


class OperationalCapabilities(BaseModel):
    capabilities: list[OperationalCapability]


class HighSeverityRisks(BaseModel):
    risks: list[str]


class HighRiskBusinessDomains(BaseModel):
    domains: list[str]


class VerdictFramework(BaseModel):
    critical_controls_by_risk: dict[str, list[str]]
    high_severity_risks: HighSeverityRisks
    high_risk_business_domains: HighRiskBusinessDomains


class KBMetadata(BaseModel):
    version: str


class KnowledgeBase(BaseModel):
    model_config = ConfigDict(extra="ignore")  # ignores sections not modelled (playbooks, etc.)

    metadata: KBMetadata
    capability_taxonomy: CapabilityTaxonomy
    threat_catalog: ThreatCatalog
    controls_catalog: ControlsCatalog
    assurance_methods: AssuranceMethods
    architecture_types: ArchitectureTypes
    operational_capabilities: OperationalCapabilities
    verdict_framework: VerdictFramework
