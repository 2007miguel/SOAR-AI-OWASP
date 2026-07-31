from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..contracts import AssessmentContext
from ..kb.service import KBService


@runtime_checkable
class Module(Protocol):
    name: str
    reads: list[str]
    writes: list[str]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext: ...
