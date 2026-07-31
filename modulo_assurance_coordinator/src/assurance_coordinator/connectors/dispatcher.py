from __future__ import annotations


class ConnectorDispatcher:
    """Launches ephemeral connector containers via the Docker/K8s runtime.

    STUB for Etapa 1. In Etapa 2+ this will use the Docker SDK (or the K8s
    Jobs API) to create short-lived containers that run a security scan and
    push results back to the coordinator.
    """

    def dispatch(self, connector: str, assessment_id: str, config: dict) -> str:
        """Launch a connector container and return a job_id. Not implemented."""
        raise NotImplementedError(
            f"Connector dispatch not available in Etapa 1 — connector: {connector}"
        )
