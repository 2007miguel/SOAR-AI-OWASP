"""Capa 3 — Coordinator resume callback tests.

Verifies that _callback_resume sends the full EvidenceBundle as a JSON body
(not empty), and that the M7 verdict signals are included.
Uses respx to intercept the outbound httpx call to the engine.
"""
from __future__ import annotations

import json

import httpx
import pytest
import respx

from assurance_coordinator.port.assurance_api import _callback_resume
from assurance_coordinator.contracts.evidence import AttestationInput, EvidenceBundle

_ENGINE = "http://engine:8000"


def _resume_url(aid: str) -> str:
    return f"{_ENGINE}/api/v1/assessments/{aid}/resume"


# ── Bundle content ─────────────────────────────────────────────────────────────

@respx.mock
def test_callback_sends_attestations_in_body():
    aid = "test-123"
    bundle = EvidenceBundle(
        assessment_id=aid,
        attestations={
            "CTRL-PROMPT-01": AttestationInput(status="implemented", evidence="audit-log"),
            "CTRL-AUTH-01": AttestationInput(status="partial"),
        },
        red_teaming_done=True,
        incident_response_plan=True,
    )
    route = respx.post(_resume_url(aid)).mock(
        return_value=httpx.Response(200, json={"verdict": "APT"})
    )
    _callback_resume(_ENGINE, aid, bundle)

    assert route.called
    payload = json.loads(route.calls[0].request.content)
    assert payload["assessment_id"] == aid
    assert "CTRL-PROMPT-01" in payload["attestations"]
    assert payload["attestations"]["CTRL-PROMPT-01"]["status"] == "implemented"
    assert payload["attestations"]["CTRL-PROMPT-01"]["evidence"] == "audit-log"
    assert payload["red_teaming_done"] is True
    assert payload["incident_response_plan"] is True


@respx.mock
def test_callback_sends_m7_verdict_signals():
    aid = "test-456"
    bundle = EvidenceBundle(
        assessment_id=aid,
        attestations={},
        red_teaming_critical_findings=True,
        supply_chain_unverified=True,
        production_access=True,
    )
    route = respx.post(_resume_url(aid)).mock(
        return_value=httpx.Response(200, json={})
    )
    _callback_resume(_ENGINE, aid, bundle)

    payload = json.loads(route.calls[0].request.content)
    assert payload["red_teaming_critical_findings"] is True
    assert payload["supply_chain_unverified"] is True
    assert payload["production_access"] is True


@respx.mock
def test_callback_m7_signals_default_to_false_when_not_set():
    aid = "test-defaults"
    bundle = EvidenceBundle(
        assessment_id=aid,
        attestations={"CTRL-A": AttestationInput(status="implemented")},
    )
    route = respx.post(_resume_url(aid)).mock(
        return_value=httpx.Response(200, json={})
    )
    _callback_resume(_ENGINE, aid, bundle)

    payload = json.loads(route.calls[0].request.content)
    assert payload["red_teaming_critical_findings"] is False
    assert payload["supply_chain_unverified"] is False
    assert payload["production_access"] is False


# ── Failure resilience ─────────────────────────────────────────────────────────

@respx.mock
def test_callback_does_not_raise_on_engine_connection_error():
    aid = "fail-connect"
    bundle = EvidenceBundle(assessment_id=aid, attestations={})
    respx.post(_resume_url(aid)).mock(
        side_effect=httpx.ConnectError("engine down")
    )
    # Must not propagate — failure is logged but the background task must not crash
    _callback_resume(_ENGINE, aid, bundle)


@respx.mock
def test_callback_does_not_raise_on_engine_http_error():
    aid = "fail-http"
    bundle = EvidenceBundle(assessment_id=aid, attestations={})
    respx.post(_resume_url(aid)).mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    _callback_resume(_ENGINE, aid, bundle)
