from __future__ import annotations

from datetime import datetime, timezone

from ..contracts import AssessmentContext
from ..contracts.context import Transition
from ..contracts.enums import Status
from ..kb.service import KBService
from ..modules import (
    M1IntakeValidation,
    M2ThreatMapper,
    M3RiskMapper,
    M4ContextEscalator,
    M5ControlResolver,
    M7VerdictEngine,
    Reporter,
    Module,
)
from ..assurance.port import AssurancePort
from .playbook import Playbook


def _build_module_registry() -> dict[str, Module]:
    return {
        "m1_intake_validation": M1IntakeValidation(),
        "m2_threat_mapper": M2ThreatMapper(),
        "m3_risk_mapper": M3RiskMapper(),
        "m4_context_escalator": M4ContextEscalator(),
        "m5_control_resolver": M5ControlResolver(),
        "m7_verdict_engine": M7VerdictEngine(),
        "reporter": Reporter(),
    }


class Orchestrator:
    """Executes a playbook over an AssessmentContext.

    Two-phase flow:
      run()    → pre-gate modules (M1–M5), then emit checklist and pause.
      resume() → post-gate modules (M7, Reporter) after attestations are collected.
    """

    def __init__(
        self,
        playbook: Playbook,
        kb: KBService,
        assurance_port: AssurancePort,
    ) -> None:
        self._playbook = playbook
        self._kb = kb
        self._assurance = assurance_port
        self._registry: dict[str, Module] = _build_module_registry()

    def run(self, ctx: AssessmentContext) -> AssessmentContext:
        """Start a new assessment. Executes pre-gate modules and pauses for assurance."""
        ctx.playbook_id = self._playbook.id

        for step in self._playbook.steps:
            if step.is_gate:
                ctx = self._assurance.emit_checklist(ctx)
                ctx.status = Status.AWAITING_ASSURANCE
                ctx.updated_at = datetime.now(timezone.utc)
                return ctx

            ctx = self._execute_module(step.module, ctx)
            if ctx.status == Status.ERROR:
                # Playbook step 1: error → ABORT + Reporter(error). The Reporter
                # produces the report; status stays ERROR (set by M1).
                ctx = self._execute_module("reporter", ctx)
                return ctx

        return ctx

    def resume(self, ctx: AssessmentContext) -> AssessmentContext:
        """Resume from AWAITING_ASSURANCE. Attestations must be in ctx.assurance."""
        if ctx.status != Status.AWAITING_ASSURANCE:
            raise ValueError(
                f"Cannot resume: expected status AWAITING_ASSURANCE, got {ctx.status.value}"
            )

        # Evidence is in (M6 complete): enter scoring while M7 computes the verdict
        # (assessment_context.txt §1). Status transitions are owned by the
        # orchestrator per the read/write matrix (§3).
        ctx.status = Status.SCORING
        ctx.updated_at = datetime.now(timezone.utc)

        past_gate = False
        for step in self._playbook.steps:
            if step.is_gate:
                past_gate = True
                continue
            if not past_gate:
                continue

            ctx = self._execute_module(step.module, ctx)
            if ctx.status == Status.ERROR:
                return ctx

        # Report generated: close the case.
        ctx.status = Status.COMPLETED
        ctx.updated_at = datetime.now(timezone.utc)
        return ctx

    def _execute_module(self, name: str, ctx: AssessmentContext) -> AssessmentContext:
        module = self._registry.get(name)
        if module is None:
            raise KeyError(f"Module '{name}' not found in registry")

        ctx = module.run(ctx, self._kb)
        ctx.transitions.append(
            Transition(
                module=name,
                timestamp=datetime.now(timezone.utc),
                status=ctx.status,
            )
        )
        ctx.updated_at = datetime.now(timezone.utc)
        return ctx
