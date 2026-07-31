from __future__ import annotations

from pydantic import BaseModel


class CriticalControl(BaseModel):
    control_id: str
    name: str
    description: str
    required_by_asi: list[str]  # ASI-IDs that mandate this control
    category: str


class RecommendedControl(BaseModel):
    control_id: str
    name: str
    description: str
    mitigates: list[str]        # T-IDs mitigated
    lifecycle_phases: list[str]


class ControlsLayer(BaseModel):
    critical_required: list[CriticalControl] = []   # sub-path A — verdict input
    recommended: list[RecommendedControl] = []       # sub-path B — filtered by lifecycle
