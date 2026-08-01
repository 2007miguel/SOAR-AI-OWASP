from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ..contracts import AssessmentContext
from ..contracts.inputs import InputsLayer
from ..contracts.assurance import Attestation, ToolResult
from ..contracts.enums import Status
from ..orchestrator import Orchestrator
from ..persistence import AssessmentStore
from ..assurance import ManualAdapter, CoordinatorAdapter
from ..kb.service import KBService
from ..modules.reporter import build_report
from .dto import (
    AttestRequest,
    AttestResponse,
    AssessmentStatusResponse,
    ChecklistItemOut,
    EvidenceBundleIn,
    StartAssessmentRequest,
    StartAssessmentResponse,
)

router = APIRouter()


# ── Dependency helpers ────────────────────────────────────────────────────────

def _orch(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

def _store(request: Request) -> AssessmentStore:
    return request.app.state.store

def _kb(request: Request) -> KBService:
    return request.app.state.kb

def _assurance(request: Request) -> ManualAdapter | CoordinatorAdapter:
    return request.app.state.assurance

def _assurance_mode(request: Request) -> str:
    return request.app.state.assurance_mode


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/assessments", status_code=201, response_model=StartAssessmentResponse)
def create_assessment(
    body: StartAssessmentRequest,
    orch: Orchestrator = Depends(_orch),
    store: AssessmentStore = Depends(_store),
    kb: KBService = Depends(_kb),
) -> StartAssessmentResponse:
    """Start a new assessment. Runs M1–M5 and returns the assurance checklist."""
    inputs = InputsLayer(
        capability_flags=body.capability_flags,
        business_context=body.business_context,
        aibom=body.aibom,
    )
    ctx = AssessmentContext(
        kb_version=kb.kb_version(),
        playbook_id="",
        inputs=inputs,
    )
    ctx = orch.run(ctx)
    store.save(ctx)

    checklist = [
        ChecklistItemOut(
            control_id=item.control_id,
            why=item.why,
            category=item.category,
            suggested_assur=item.suggested_assur,
        )
        for item in ctx.assurance.checklist
    ]

    errors = ctx.analysis.validation.errors if ctx.analysis.validation else []

    return StartAssessmentResponse(
        assessment_id=ctx.assessment_id,
        status=ctx.status.value,
        checklist=checklist,
        warnings=ctx.analysis.warnings,
        errors=errors,
    )


@router.post("/assessments/{assessment_id}/attest", response_model=AttestResponse)
def attest(
    assessment_id: str,
    body: AttestRequest,
    store: AssessmentStore = Depends(_store),
    assurance: ManualAdapter | CoordinatorAdapter = Depends(_assurance),
    assurance_mode: str = Depends(_assurance_mode),
) -> AttestResponse:
    """Submit attestations for one or more controls. Can be called multiple times.

    In coordinator mode the payload is forwarded to the coordinator; the engine
    does not write to its own store. In manual mode (Etapa 0) the engine handles
    attestations directly.
    """
    ctx = _load_or_404(store, assessment_id)
    _require_status(ctx, Status.AWAITING_ASSURANCE)

    if assurance_mode == "coordinator":
        result = assurance.forward_attestation(
            assessment_id,
            body.model_dump(mode="json"),
        )
        return AttestResponse(
            assessment_id=assessment_id,
            status=ctx.status.value,
            is_ready=result.get("is_ready", False),
        )

    # ── Manual mode (Etapa 0): write directly to ctx ──────────────────────────
    for ctrl_id, att in body.attestations.items():
        ctx.assurance.attestations[ctrl_id] = Attestation(
            status=att.status,
            evidence=att.evidence,
            assurance_method=att.assurance_method,
        )

    if body.incident_response_plan is not None:
        ctx.assurance.incident_response_plan = body.incident_response_plan
    if body.red_teaming_done is not None:
        ctx.assurance.red_teaming_done = body.red_teaming_done
    if body.red_teaming_critical_findings is not None:
        ctx.assurance.red_teaming_critical_findings = body.red_teaming_critical_findings
    if body.supply_chain_unverified is not None:
        ctx.assurance.supply_chain_unverified = body.supply_chain_unverified
    if body.production_access is not None:
        ctx.assurance.production_access = body.production_access
    if body.assurance_methods_used:
        existing = set(ctx.assurance.assurance_methods_used)
        ctx.assurance.assurance_methods_used = list(
            existing | set(body.assurance_methods_used)
        )

    store.update(ctx)

    return AttestResponse(
        assessment_id=assessment_id,
        status=ctx.status.value,
        is_ready=assurance.is_ready(ctx),
    )


@router.post("/assessments/{assessment_id}/resume")
def resume_assessment(
    assessment_id: str,
    body: EvidenceBundleIn | None = Body(default=None),
    orch: Orchestrator = Depends(_orch),
    store: AssessmentStore = Depends(_store),
    assurance: ManualAdapter | CoordinatorAdapter = Depends(_assurance),
    assurance_mode: str = Depends(_assurance_mode),
) -> dict:
    """Resume the pipeline after attestations. Runs M7 + Reporter and returns the report.

    In coordinator mode the EvidenceBundle (sent by the coordinator's callback)
    is required — it populates ctx.assurance before M7 runs. In manual mode the
    attestations are already in ctx.assurance (written by /attest) and no body is
    expected.
    """
    ctx = _load_or_404(store, assessment_id)
    _require_status(ctx, Status.AWAITING_ASSURANCE)

    if assurance_mode == "coordinator":
        if body is None:
            raise HTTPException(
                status_code=422,
                detail="EvidenceBundle body is required in coordinator mode",
            )
        # Populate ctx.assurance from the bundle sent by the coordinator
        for ctrl_id, att_in in body.attestations.items():
            ctx.assurance.attestations[ctrl_id] = Attestation(
                status=att_in.status,
                evidence=att_in.evidence,
                assurance_method=att_in.assurance_method,
            )
        ctx.assurance.tool_results = [
            ToolResult(**tr.model_dump()) for tr in body.tool_results
        ]
        ctx.assurance.red_teaming_done = body.red_teaming_done
        ctx.assurance.incident_response_plan = body.incident_response_plan
        ctx.assurance.assurance_methods_used = body.assurance_methods_used
        ctx.assurance.red_teaming_critical_findings = body.red_teaming_critical_findings
        ctx.assurance.supply_chain_unverified = body.supply_chain_unverified
        ctx.assurance.production_access = body.production_access

    if not assurance.is_ready(ctx):
        raise HTTPException(
            status_code=400,
            detail="Not all critical controls have been attested",
        )

    ctx = orch.resume(ctx)
    store.update(ctx)
    return build_report(ctx)


@router.get("/assessments/{assessment_id}", response_model=AssessmentStatusResponse)
def get_assessment(
    assessment_id: str,
    store: AssessmentStore = Depends(_store),
) -> AssessmentStatusResponse:
    """Get the current status and, if completed, the full report."""
    ctx = _load_or_404(store, assessment_id)
    report = build_report(ctx) if ctx.status == Status.COMPLETED else None

    return AssessmentStatusResponse(
        assessment_id=ctx.assessment_id,
        kb_version=ctx.kb_version,
        status=ctx.status.value,
        report=report,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_or_404(store: AssessmentStore, assessment_id: str) -> AssessmentContext:
    ctx = store.get(assessment_id)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment '{assessment_id}' not found",
        )
    return ctx


def _require_status(ctx: AssessmentContext, expected: Status) -> None:
    if ctx.status != expected:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Assessment is in status '{ctx.status.value}', "
                f"expected '{expected.value}'"
            ),
        )
