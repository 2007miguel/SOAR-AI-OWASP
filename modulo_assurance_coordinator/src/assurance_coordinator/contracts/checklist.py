from __future__ import annotations

from pydantic import BaseModel


class ChecklistItem(BaseModel):
    control_id: str
    why: list[str]               # ASI-IDs that require this control
    category: str
    suggested_assur: list[str]   # ASSUR-IDs recommended for coverage


class ChecklistBundle(BaseModel):
    assessment_id: str
    active_asi: list[str]
    items: list[ChecklistItem]
