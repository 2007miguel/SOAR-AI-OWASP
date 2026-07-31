from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from ..attestation.intake import AttestationIntake
from ..attestation.partial_store import PartialStore
from ..checklist.presenter import ChecklistPresenter
from ..contracts.checklist import ChecklistBundle
from ..contracts.evidence import AttestationInput
from ..persistence.job_store import JobStore

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Dependency helpers ──────────────────────────────────────────────────────


def _store(request: Request) -> JobStore:
    return request.app.state.store  # type: ignore[no-any-return]


def _intake(request: Request) -> AttestationIntake:
    return request.app.state.intake  # type: ignore[no-any-return]


def _partial(request: Request) -> PartialStore:
    return request.app.state.partial_store  # type: ignore[no-any-return]


def _presenter(request: Request) -> ChecklistPresenter:
    return request.app.state.presenter  # type: ignore[no-any-return]


def _engine_url(request: Request) -> str:
    return request.app.state.engine_url  # type: ignore[no-any-return]


# ── DTOs ────────────────────────────────────────────────────────────────────


class AttestRequest(BaseModel):
    attestations: dict[str, AttestationInput] = {}
    incident_response_plan: bool | None = None   # None = leave unchanged
    red_teaming_done: bool | None = None          # None = leave unchanged
    assurance_methods_used: list[str] = []
    # Optional verdict signals consumed by the engine's M7 (aligned with the
    # engine's AttestRequest). None = leave unchanged.
    red_teaming_critical_findings: bool | None = None
    supply_chain_unverified: bool | None = None
    production_access: bool | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/checklist", status_code=201)
def receive_checklist(
    body: ChecklistBundle,
    store: JobStore = Depends(_store),
    presenter: ChecklistPresenter = Depends(_presenter),
) -> dict:
    """Called by the engine when an assessment reaches AWAITING_ASSURANCE.

    Creates a coordinator session and logs the pending controls. Idempotent:
    if a session already exists for this assessment, it is left untouched (a
    retried delivery must not wipe accumulated attestations).
    """
    if store.get_session(body.assessment_id) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Coordinator session for '{body.assessment_id}' already exists",
        )

    store.create_session(
        assessment_id=body.assessment_id,
        active_asi=body.active_asi,
        checklist=[item.model_dump() for item in body.items],
    )
    summary = presenter.summary(body)
    logger.info(
        "Session created — assessment=%s controls=%d",
        body.assessment_id,
        len(body.items),
    )
    return {
        "assessment_id": body.assessment_id,
        "controls_pending": len(body.items),
        "summary": summary,
    }


@router.post("/attest/{assessment_id}")
def submit_attestations(
    assessment_id: str,
    body: AttestRequest,
    background_tasks: BackgroundTasks,
    store: JobStore = Depends(_store),
    intake: AttestationIntake = Depends(_intake),
    partial: PartialStore = Depends(_partial),
    engine_url: str = Depends(_engine_url),
) -> dict:
    """Called by the engine to forward each HITL attestation update.

    On the transition to ready, marks the session and fires the resume callback
    to the engine exactly once (subsequent updates do not re-fire).
    """
    session = store.get_session(assessment_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"No coordinator session for assessment '{assessment_id}'",
        )
    was_ready = session.status == "ready"

    is_ready = intake.submit(
        assessment_id=assessment_id,
        attestations=body.attestations,
        incident_response_plan=body.incident_response_plan,
        red_teaming_done=body.red_teaming_done,
        assurance_methods_used=body.assurance_methods_used or [],
        red_teaming_critical_findings=body.red_teaming_critical_findings,
        supply_chain_unverified=body.supply_chain_unverified,
        production_access=body.production_access,
    )

    pending = partial.get_pending(assessment_id)
    logger.info(
        "Attestation update — assessment=%s is_ready=%s pending=%s",
        assessment_id,
        is_ready,
        pending,
    )

    # Fire the resume callback only on the pending → ready transition. The
    # callback runs in the background so a slow/unreachable engine never blocks
    # the attestation response.
    if is_ready and not was_ready:
        store.mark_ready(assessment_id)
        background_tasks.add_task(_callback_resume, engine_url, assessment_id)

    return {
        "assessment_id": assessment_id,
        "is_ready": is_ready,
        "pending_controls": pending,
    }


@router.get("/status/{assessment_id}")
def get_status(
    assessment_id: str,
    store: JobStore = Depends(_store),
    partial: PartialStore = Depends(_partial),
) -> dict:
    """Engine can poll readiness. Returns pending controls and session status."""
    data = store.get_session(assessment_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No coordinator session for assessment '{assessment_id}'",
        )

    is_ready = store.is_ready(assessment_id)
    pending = partial.get_pending(assessment_id)

    return {
        "assessment_id": assessment_id,
        "is_ready": is_ready,
        "pending_controls": pending,
        "status": data.status,
    }


# ── Internal callback ───────────────────────────────────────────────────────


def _callback_resume(engine_url: str, assessment_id: str) -> None:
    """POST to the engine's /resume endpoint to continue the pipeline."""
    url = f"{engine_url}/api/v1/assessments/{assessment_id}/resume"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url)
            resp.raise_for_status()
        logger.info(
            "Resume callback sent — assessment=%s status=%d",
            assessment_id,
            resp.status_code,
        )
    except httpx.HTTPError as exc:
        logger.error(
            "Resume callback failed — assessment=%s error=%s",
            assessment_id,
            exc,
        )
