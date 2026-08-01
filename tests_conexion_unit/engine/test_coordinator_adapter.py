"""Capa 1 — CoordinatorAdapter unit tests.

Uses respx to intercept outbound httpx calls. No real network, no Docker.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi import HTTPException

from validation_engine.assurance.coordinator_adapter import CoordinatorAdapter
from validation_engine.contracts.controls import CriticalControl

_COORD = "http://coordinator:8100"
_CTRL = CriticalControl(
    control_id="CTRL-PROMPT-01",
    name="Prompt Injection Defense",
    description="Mitigate prompt injection",
    required_by_asi=["ASI01"],
    category="Prevention",
)


@pytest.fixture
def adapter(fake_kb) -> CoordinatorAdapter:
    return CoordinatorAdapter(fake_kb, _COORD)


@pytest.fixture
def ctx_with_one_control(ctx_awaiting):
    ctx_awaiting.controls.critical_required = [_CTRL]
    ctx_awaiting.analysis.active_asi = ["ASI01"]
    return ctx_awaiting


# ── emit_checklist ─────────────────────────────────────────────────────────────

@respx.mock
def test_emit_checklist_posts_correct_payload(adapter, ctx_with_one_control):
    route = respx.post(f"{_COORD}/api/v1/checklist").mock(
        return_value=httpx.Response(201, json={"controls_pending": 1})
    )
    adapter.emit_checklist(ctx_with_one_control)

    assert route.called
    payload = json.loads(route.calls[0].request.content)
    assert payload["assessment_id"] == ctx_with_one_control.assessment_id
    assert payload["active_asi"] == ["ASI01"]
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["control_id"] == "CTRL-PROMPT-01"
    assert "why" in item
    assert "category" in item
    assert "suggested_assur" in item


@respx.mock
def test_emit_checklist_builds_local_checklist_before_posting(adapter, ctx_with_one_control):
    respx.post(f"{_COORD}/api/v1/checklist").mock(
        return_value=httpx.Response(201, json={})
    )
    assert ctx_with_one_control.assurance.checklist == []
    adapter.emit_checklist(ctx_with_one_control)
    assert len(ctx_with_one_control.assurance.checklist) == 1
    assert ctx_with_one_control.assurance.checklist[0].control_id == "CTRL-PROMPT-01"


@respx.mock
def test_emit_checklist_tolerates_409_idempotent(adapter, ctx_with_one_control):
    respx.post(f"{_COORD}/api/v1/checklist").mock(
        return_value=httpx.Response(409)
    )
    # A 409 means the session already exists — must not raise.
    result = adapter.emit_checklist(ctx_with_one_control)
    assert result is ctx_with_one_control


@respx.mock
def test_emit_checklist_raises_502_when_coordinator_unreachable(adapter, ctx_with_one_control):
    respx.post(f"{_COORD}/api/v1/checklist").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    with pytest.raises(HTTPException) as exc:
        adapter.emit_checklist(ctx_with_one_control)
    assert exc.value.status_code == 502
    assert "unavailable" in exc.value.detail.lower()


# ── forward_attestation ────────────────────────────────────────────────────────

@respx.mock
def test_forward_attestation_proxies_payload_verbatim(adapter):
    aid = "test-assessment-id"
    payload = {
        "attestations": {"CTRL-PROMPT-01": {"status": "implemented", "evidence": "logs"}},
        "incident_response_plan": True,
        "red_teaming_done": True,
    }
    route = respx.post(f"{_COORD}/api/v1/attest/{aid}").mock(
        return_value=httpx.Response(200, json={"is_ready": True, "pending_controls": []})
    )
    result = adapter.forward_attestation(aid, payload)

    assert route.called
    sent = json.loads(route.calls[0].request.content)
    assert sent == payload
    assert result["is_ready"] is True
    assert result["pending_controls"] == []


@respx.mock
def test_forward_attestation_propagates_coordinator_404(adapter):
    aid = "missing-session"
    respx.post(f"{_COORD}/api/v1/attest/{aid}").mock(
        return_value=httpx.Response(404, text="No coordinator session")
    )
    with pytest.raises(HTTPException) as exc:
        adapter.forward_attestation(aid, {})
    assert exc.value.status_code == 404


@respx.mock
def test_forward_attestation_raises_502_when_coordinator_unreachable(adapter):
    aid = "some-id"
    respx.post(f"{_COORD}/api/v1/attest/{aid}").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    with pytest.raises(HTTPException) as exc:
        adapter.forward_attestation(aid, {})
    assert exc.value.status_code == 502
