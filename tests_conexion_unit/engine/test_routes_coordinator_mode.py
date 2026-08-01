"""Capa 2 — Engine API routes in coordinator mode.

Uses FastAPI's TestClient with a minimal app (no lifespan, no DB, no KB).
Fake adapters replace real services so these tests run with no infrastructure.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from validation_engine.api.routes import router
from validation_engine.contracts.assurance import Attestation
from validation_engine.contracts.enums import AttestationStatus

from .conftest import FakeCoordinatorAdapter, FakeManualAdapter


# ── Test-app factory ───────────────────────────────────────────────────────────

def _make_client(
    store,
    orchestrator,
    assurance,
    assurance_mode: str,
) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.store = store
    app.state.orchestrator = orchestrator
    app.state.assurance = assurance
    app.state.assurance_mode = assurance_mode
    app.state.kb = None  # not accessed by attest/resume routes
    return TestClient(app, raise_server_exceptions=True)


# ── /attest — coordinator mode ─────────────────────────────────────────────────

def test_attest_coordinator_calls_forward_attestation(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    resp = client.post(f"/api/v1/assessments/{aid}/attest", json={
        "attestations": {"CTRL-A": {"status": "implemented", "evidence": "log"}},
        "incident_response_plan": True,
    })

    assert resp.status_code == 200
    assert fake_coordinator_adapter.forward_called_with is not None
    assert fake_coordinator_adapter.forward_called_with[0] == aid


def test_attest_coordinator_does_not_write_to_local_store(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    client.post(f"/api/v1/assessments/{aid}/attest", json={
        "attestations": {"CTRL-A": {"status": "implemented"}},
    })

    # In coordinator mode the engine must NOT write attestations locally.
    stored = fake_store.get(aid)
    assert stored.assurance.attestations == {}


def test_attest_coordinator_returns_coordinator_is_ready(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter_ready
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter_ready, "coordinator")
    aid = ctx_awaiting.assessment_id

    resp = client.post(f"/api/v1/assessments/{aid}/attest", json={"attestations": {}})

    assert resp.status_code == 200
    assert resp.json()["is_ready"] is True


# ── /resume — coordinator mode ────────────────────────────────────────────────

def test_resume_coordinator_requires_evidence_bundle(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    # No body → 422
    resp = client.post(f"/api/v1/assessments/{aid}/resume")
    assert resp.status_code == 422


def test_resume_coordinator_populates_ctx_assurance_from_bundle(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    bundle = {
        "assessment_id": aid,
        "attestations": {
            "CTRL-A": {"status": "implemented", "evidence": "log-A"},
            "CTRL-B": {"status": "implemented", "evidence": "log-B"},
        },
        "red_teaming_done": True,
        "incident_response_plan": True,
        "red_teaming_critical_findings": False,
        "supply_chain_unverified": False,
        "production_access": False,
    }
    resp = client.post(f"/api/v1/assessments/{aid}/resume", json=bundle)

    assert resp.status_code == 200
    # SpyOrchestrator captured the ctx just before M7 — attestations must be there
    resumed = spy_orchestrator.resumed_ctx
    assert resumed is not None
    assert "CTRL-A" in resumed.assurance.attestations
    assert resumed.assurance.attestations["CTRL-A"].status == AttestationStatus.IMPLEMENTED
    assert resumed.assurance.incident_response_plan is True
    assert resumed.assurance.red_teaming_done is True


def test_resume_coordinator_m7_signals_propagate_from_bundle(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    bundle = {
        "assessment_id": aid,
        "attestations": {
            "CTRL-A": {"status": "implemented"},
            "CTRL-B": {"status": "implemented"},
        },
        "red_teaming_critical_findings": True,
        "supply_chain_unverified": True,
        "production_access": True,
    }
    client.post(f"/api/v1/assessments/{aid}/resume", json=bundle)

    resumed = spy_orchestrator.resumed_ctx
    assert resumed.assurance.red_teaming_critical_findings is True
    assert resumed.assurance.supply_chain_unverified is True
    assert resumed.assurance.production_access is True


def test_resume_coordinator_returns_400_if_bundle_attestations_incomplete(
    ctx_awaiting, fake_store, spy_orchestrator, fake_coordinator_adapter
):
    client = _make_client(fake_store, spy_orchestrator, fake_coordinator_adapter, "coordinator")
    aid = ctx_awaiting.assessment_id

    # ctx has CTRL-A and CTRL-B critical; bundle only attests CTRL-A
    bundle = {
        "assessment_id": aid,
        "attestations": {
            "CTRL-A": {"status": "implemented"},
        },
    }
    resp = client.post(f"/api/v1/assessments/{aid}/resume", json=bundle)
    assert resp.status_code == 400


# ── /resume — manual mode regression ──────────────────────────────────────────

def test_resume_manual_mode_works_without_body(
    ctx_ready, fake_store_ready, spy_orchestrator, fake_manual_adapter
):
    client = _make_client(fake_store_ready, spy_orchestrator, fake_manual_adapter, "manual")
    aid = ctx_ready.assessment_id

    # Manual mode: attestations are already in the store; no body needed
    resp = client.post(f"/api/v1/assessments/{aid}/resume")

    assert resp.status_code == 200
    assert resp.json()["verdict"] == "APT"
