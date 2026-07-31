from __future__ import annotations


class ConnectorClient:
    """Uniform HTTP interface for calling a running connector container.

    Each connector exposes a /run endpoint that accepts a target + config and
    returns raw evidence. STUB for Etapa 1 — connectors are not launched yet.
    """

    def run(self, base_url: str, target: str, config: dict) -> dict:
        """Call the connector's /run endpoint and return raw evidence. Not implemented."""
        raise NotImplementedError("Connector client not available in Etapa 1")
