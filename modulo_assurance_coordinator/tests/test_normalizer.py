from __future__ import annotations

from assurance_coordinator.contracts.evidence import AttestationInput, AttestationStatus
from assurance_coordinator.normalizer.evidence_mapper import EvidenceMapper


def test_normalize_tool_result_maps_raw_dict():
    mapper = EvidenceMapper()
    raw = {"verdict": "fail", "findings": [{"id": "F1", "severity": "high"}], "ref": "s3://x"}
    result = mapper.normalize_tool_result(raw, "connector-zap")
    assert result.connector == "connector-zap"
    assert result.verdict == "fail"
    assert result.findings == [{"id": "F1", "severity": "high"}]
    assert result.raw_ref == "s3://x"


def test_normalize_tool_result_defaults_on_missing_fields():
    mapper = EvidenceMapper()
    result = mapper.normalize_tool_result({}, "connector-trivy")
    assert result.verdict == "unknown"
    assert result.findings == []
    assert result.raw_ref is None


def test_build_bundle_carries_all_verdict_signals():
    """EvidenceBundle must expose the three M7 verdict signals (contract alignment)."""
    mapper = EvidenceMapper()
    bundle = mapper.build_bundle(
        assessment_id="A1",
        attestations={"CTRL-MON-01": AttestationInput(status=AttestationStatus.IMPLEMENTED)},
        red_teaming_done=True,
        incident_response_plan=True,
        assurance_methods_used=["ASSUR-01"],
    )
    # Fields required by the engine's M7 verdict engine.
    assert hasattr(bundle, "production_access")
    assert hasattr(bundle, "supply_chain_unverified")
    assert hasattr(bundle, "red_teaming_critical_findings")
    assert bundle.production_access is False
    assert bundle.supply_chain_unverified is False
    assert bundle.red_teaming_critical_findings is False
