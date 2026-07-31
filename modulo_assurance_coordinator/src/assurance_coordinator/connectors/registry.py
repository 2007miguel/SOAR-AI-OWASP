from __future__ import annotations


class ConnectorRegistry:
    """Catalog of available connector images.

    Empty in Etapa 1. In Etapa 2+ each connector registers here with its
    Docker image name and the ASSUR-IDs it covers.
    """

    def list_connectors(self) -> list[str]:
        return []

    def covers(self, assur_id: str) -> list[str]:
        """Return connector names capable of covering the given ASSUR-ID."""
        return []
