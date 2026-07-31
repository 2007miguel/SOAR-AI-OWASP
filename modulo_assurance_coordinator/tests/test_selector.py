from __future__ import annotations

from assurance_coordinator.connectors.registry import ConnectorRegistry
from assurance_coordinator.connectors.selector import ConnectorSelector


def test_selector_empty_in_etapa1():
    """No connectors registered → nothing to run (HITL-only stage)."""
    selector = ConnectorSelector(ConnectorRegistry())
    assert selector.select(["ASI01", "ASI02"], ["ASSUR-01", "ASSUR-05"]) == []


def test_selector_deduplicates_across_assur_ids():
    """When a connector covers several ASSUR-IDs it is selected only once."""

    class StubRegistry(ConnectorRegistry):
        def covers(self, assur_id: str) -> list[str]:
            return {
                "ASSUR-01": ["connector-zap", "connector-promptfoo"],
                "ASSUR-05": ["connector-zap", "connector-trivy"],
            }.get(assur_id, [])

    selector = ConnectorSelector(StubRegistry())
    result = selector.select(["ASI02"], ["ASSUR-01", "ASSUR-05"])
    assert result == ["connector-promptfoo", "connector-trivy", "connector-zap"]
