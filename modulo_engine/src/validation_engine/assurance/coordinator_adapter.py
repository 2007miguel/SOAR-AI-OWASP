from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from ..contracts import AssessmentContext
from ..contracts.assurance import ChecklistItem
from ..contracts.enums import AttestationStatus
from ..kb.service import KBService

logger = logging.getLogger(__name__)


class CoordinatorAdapter:
    """Etapa 1: assurance plane delegated to the coordinator service over HTTP.

    emit_checklist builds the local checklist (identical logic to ManualAdapter)
    and notifies the coordinator so it can open its session. Fails fast (502) if
    the coordinator is unreachable — an orphaned assessment with no session would
    be unrecoverable.

    is_ready checks ctx.assurance.attestations locally. In coordinator mode those
    attestations arrive only inside the EvidenceBundle sent with the /resume
    callback, so is_ready is only meaningful at that point.

    forward_attestation proxies the engine's /attest payload to the coordinator
    without writing anything to the engine's own store.
    """

    def __init__(self, kb: KBService, coordinator_url: str) -> None:
        self._kb = kb
        self._coordinator_url = coordinator_url.rstrip("/")

    # ── AssurancePort interface ────────────────────────────────────────────────

    def emit_checklist(self, ctx: AssessmentContext) -> AssessmentContext:
        for ctrl in ctx.controls.critical_required:
            ctx.assurance.checklist.append(
                ChecklistItem(
                    control_id=ctrl.control_id,
                    why=ctrl.required_by_asi,
                    category=ctrl.category,
                    suggested_assur=self._suggested_assur(ctrl.required_by_asi),
                    status=AttestationStatus.NOT_IMPLEMENTED,
                )
            )
        self._post_checklist(ctx)
        return ctx

    def is_ready(self, ctx: AssessmentContext) -> bool:
        critical_ids = {c.control_id for c in ctx.controls.critical_required}
        return critical_ids.issubset(set(ctx.assurance.attestations.keys()))

    # ── Extra method for coordinator mode ─────────────────────────────────────

    def forward_attestation(self, assessment_id: str, payload: dict) -> dict:
        """Proxy an attestation request to the coordinator.

        Returns the coordinator's response dict (is_ready, pending_controls).
        """
        url = f"{self._coordinator_url}/api/v1/attest/{assessment_id}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=exc.response.text,
            ) from exc
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to forward attestation to coordinator — assessment=%s error=%s",
                assessment_id,
                exc,
            )
            raise HTTPException(
                status_code=502,
                detail="Coordinator unavailable — could not forward attestation",
            ) from exc

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _post_checklist(self, ctx: AssessmentContext) -> None:
        payload = {
            "assessment_id": ctx.assessment_id,
            "active_asi": ctx.analysis.active_asi,
            "items": [
                {
                    "control_id": item.control_id,
                    "why": item.why,
                    "category": item.category,
                    "suggested_assur": item.suggested_assur,
                }
                for item in ctx.assurance.checklist
            ],
        }
        url = f"{self._coordinator_url}/api/v1/checklist"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 409:
                    logger.warning(
                        "Checklist already registered in coordinator — assessment=%s",
                        ctx.assessment_id,
                    )
                    return
                resp.raise_for_status()
            logger.info(
                "Checklist sent to coordinator — assessment=%s controls=%d",
                ctx.assessment_id,
                len(ctx.assurance.checklist),
            )
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to send checklist to coordinator — assessment=%s error=%s",
                ctx.assessment_id,
                exc,
            )
            raise HTTPException(
                status_code=502,
                detail="Coordinator unavailable — could not create assurance session",
            ) from exc

    def _suggested_assur(self, required_by_asi: list[str]) -> list[str]:
        methods: set[str] = set()
        for asi_id in required_by_asi:
            methods.update(self._kb.assurance_methods_for_asi(asi_id))
        return sorted(methods)
