"""Shared fixtures and fakes for engine connection tests."""
from __future__ import annotations

import pytest

from validation_engine.contracts.context import AssessmentContext
from validation_engine.contracts.inputs import InputsLayer, CapabilityFlags, BusinessContext
from validation_engine.contracts.controls import CriticalControl
from validation_engine.contracts.assurance import AssuranceLayer, Attestation
from validation_engine.contracts.verdict import VerdictLayer, VerdictTrace
from validation_engine.contracts.enums import (
    Status,
    VerdictResult,
    BusinessDomain,
    ArchitectureId,
    LifecyclePhase,
    AttestationStatus,
)

# Two minimal test controls — intentionally small so test assertions are readable
_CTRL_A = CriticalControl(
    control_id="CTRL-A",
    name="Control A",
    description="Test control A",
    required_by_asi=["ASI01"],
    category="Prevention",
)
_CTRL_B = CriticalControl(
    control_id="CTRL-B",
    name="Control B",
    description="Test control B",
    required_by_asi=["ASI02"],
    category="Detection",
)

_COMPLETED_VERDICT = VerdictLayer(
    result=VerdictResult.APT,
    label="Apt for Production",
    rationale="All controls implemented.",
    blocking_reasons=[],
    trace=VerdictTrace(),
)


def _build_ctx(
    status: Status = Status.AWAITING_ASSURANCE,
    with_attestations: bool = False,
) -> AssessmentContext:
    ctx = AssessmentContext(
        kb_version="1.0",
        playbook_id="test",
        status=status,
        inputs=InputsLayer(
            capability_flags=CapabilityFlags(),
            business_context=BusinessContext(
                business_domain=BusinessDomain.TECHNOLOGY,
                architecture_id=ArchitectureId.SINGLE,
                lifecycle_phases=[LifecyclePhase.RUNTIME],
            ),
        ),
    )
    ctx.controls.critical_required = [_CTRL_A, _CTRL_B]
    if with_attestations:
        ctx.assurance.attestations = {
            "CTRL-A": Attestation(status=AttestationStatus.IMPLEMENTED, evidence="proof-A"),
            "CTRL-B": Attestation(status=AttestationStatus.IMPLEMENTED, evidence="proof-B"),
        }
        ctx.assurance.incident_response_plan = True
    return ctx


# ── In-memory store ────────────────────────────────────────────────────────────

class FakeStore:
    def __init__(self) -> None:
        self._data: dict[str, AssessmentContext] = {}

    def get(self, assessment_id: str) -> AssessmentContext | None:
        return self._data.get(assessment_id)

    def save(self, ctx: AssessmentContext) -> None:
        self._data[ctx.assessment_id] = ctx

    def update(self, ctx: AssessmentContext) -> None:
        self._data[ctx.assessment_id] = ctx


# ── Spy orchestrator ───────────────────────────────────────────────────────────

class SpyOrchestrator:
    """Records the ctx passed to resume() and stamps it COMPLETED/APT."""

    def __init__(self) -> None:
        self.resumed_ctx: AssessmentContext | None = None

    def resume(self, ctx: AssessmentContext) -> AssessmentContext:
        self.resumed_ctx = ctx
        ctx.status = Status.COMPLETED
        ctx.verdict = _COMPLETED_VERDICT
        return ctx


# ── Fake adapters ──────────────────────────────────────────────────────────────

class FakeCoordinatorAdapter:
    """CoordinatorAdapter stand-in — no HTTP, records calls."""

    def __init__(self, forward_result: dict | None = None) -> None:
        self.emit_called_ctx: AssessmentContext | None = None
        self.forward_called_with: tuple | None = None
        self._forward_result = forward_result or {
            "is_ready": False,
            "pending_controls": ["CTRL-A", "CTRL-B"],
        }

    def emit_checklist(self, ctx: AssessmentContext) -> AssessmentContext:
        self.emit_called_ctx = ctx
        return ctx

    def is_ready(self, ctx: AssessmentContext) -> bool:
        critical_ids = {c.control_id for c in ctx.controls.critical_required}
        return critical_ids.issubset(set(ctx.assurance.attestations.keys()))

    def forward_attestation(self, assessment_id: str, payload: dict) -> dict:
        self.forward_called_with = (assessment_id, payload)
        return self._forward_result


class FakeManualAdapter:
    """ManualAdapter stand-in — no KB needed, pure in-memory."""

    def emit_checklist(self, ctx: AssessmentContext) -> AssessmentContext:
        return ctx

    def is_ready(self, ctx: AssessmentContext) -> bool:
        critical_ids = {c.control_id for c in ctx.controls.critical_required}
        return critical_ids.issubset(set(ctx.assurance.attestations.keys()))


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ctx_awaiting() -> AssessmentContext:
    return _build_ctx()


@pytest.fixture
def ctx_ready() -> AssessmentContext:
    return _build_ctx(with_attestations=True)


@pytest.fixture
def fake_store(ctx_awaiting: AssessmentContext) -> FakeStore:
    store = FakeStore()
    store.save(ctx_awaiting)
    return store


@pytest.fixture
def fake_store_ready(ctx_ready: AssessmentContext) -> FakeStore:
    store = FakeStore()
    store.save(ctx_ready)
    return store


@pytest.fixture
def spy_orchestrator() -> SpyOrchestrator:
    return SpyOrchestrator()


@pytest.fixture
def fake_coordinator_adapter() -> FakeCoordinatorAdapter:
    return FakeCoordinatorAdapter()


@pytest.fixture
def fake_coordinator_adapter_ready() -> FakeCoordinatorAdapter:
    return FakeCoordinatorAdapter(
        forward_result={"is_ready": True, "pending_controls": []}
    )


@pytest.fixture
def fake_manual_adapter() -> FakeManualAdapter:
    return FakeManualAdapter()


@pytest.fixture
def fake_kb():
    from unittest.mock import MagicMock
    kb = MagicMock()
    kb.assurance_methods_for_asi.return_value = ["ASSUR-01"]
    return kb
