from __future__ import annotations

from .registry import ConnectorRegistry


class ConnectorSelector:
    """Maps active ASIs and ASSUR-IDs to the set of connectors that should run.

    Returns empty list in Etapa 1 (no connectors registered).
    """

    def __init__(self, registry: ConnectorRegistry) -> None:
        self._registry = registry

    def select(self, active_asi: list[str], assur_ids: list[str]) -> list[str]:
        connectors: set[str] = set()
        for assur_id in assur_ids:
            connectors.update(self._registry.covers(assur_id))
        return sorted(connectors)
