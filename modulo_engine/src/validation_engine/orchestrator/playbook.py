from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator


class PlaybookStep(BaseModel):
    module: str | None = None
    assurance_gate: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "PlaybookStep":
        if (self.module is None) == (self.assurance_gate is None):
            raise ValueError(
                "Each playbook step must have exactly one of: module, assurance_gate"
            )
        return self

    @property
    def is_gate(self) -> bool:
        return self.assurance_gate is not None


class Playbook(BaseModel):
    id: str
    version: str
    description: str = ""
    steps: list[PlaybookStep]


def load_playbook(path: str | Path) -> Playbook:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Playbook.model_validate(data)
