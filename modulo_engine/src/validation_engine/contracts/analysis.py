from __future__ import annotations

from pydantic import BaseModel


class ValidationResult(BaseModel):
    ok: bool
    errors: list[dict] = []  # {code, message} — blocking


class ArchitectureRecos(BaseModel):
    security_practices: list[dict] = []
    priority_control_domains: list[str] = []


class AnalysisLayer(BaseModel):
    # M1 — Intake & Validation
    validation: ValidationResult | None = None
    warnings: list[dict] = []  # {code, message} — non-blocking

    # M2 — ThreatMapper
    active_steps: list[str] = []               # ["STEP-1", "STEP-3"]
    active_threats: list[str] = []             # ["T2", "T6"]
    threat_source_map: dict[str, list[str]] = {}  # T-ID → [flags/steps]
    critical_systems_path: bool = False

    # M3 — RiskMapper
    active_asi: list[str] = []                 # ["ASI01", "ASI06"]
    asi_trace: dict[str, list[str]] = {}       # ASI-ID → [T-IDs]

    # M4 — ContextEscalator
    high_risk_domain: bool = False
    hotl_required: bool = False
    architecture_recos: ArchitectureRecos | None = None
    escalations: list[dict] = []              # {rule, effect}
