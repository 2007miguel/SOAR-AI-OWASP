from __future__ import annotations

from pydantic import BaseModel

from .enums import VerdictResult


class VerdictTrace(BaseModel):
    flags_to_threats: dict[str, list[str]] = {}   # flag → [T-IDs]
    threats_to_risks: dict[str, list[str]] = {}   # T-ID → [ASI-IDs]
    risks_to_controls: dict[str, list[str]] = {}  # ASI-ID → [CTRL-IDs]


class VerdictLayer(BaseModel):
    result: VerdictResult
    label: str
    rationale: str
    blocking_reasons: list[str] = []
    trace: VerdictTrace
