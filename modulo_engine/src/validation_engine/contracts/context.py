from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .enums import Status
from .inputs import InputsLayer
from .analysis import AnalysisLayer
from .controls import ControlsLayer
from .assurance import AssuranceLayer
from .verdict import VerdictLayer


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Transition(BaseModel):
    module: str
    timestamp: datetime
    status: Status


class AssessmentContext(BaseModel):
    assessment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kb_version: str
    schema_version: str = "1.0"
    playbook_id: str
    status: Status = Status.INTAKE
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    transitions: list[Transition] = []

    inputs: InputsLayer
    analysis: AnalysisLayer = Field(default_factory=AnalysisLayer)
    controls: ControlsLayer = Field(default_factory=ControlsLayer)
    assurance: AssuranceLayer = Field(default_factory=AssuranceLayer)
    verdict: VerdictLayer | None = None
