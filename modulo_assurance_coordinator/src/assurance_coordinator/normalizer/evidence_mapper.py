from __future__ import annotations

from ..contracts.evidence import AttestationInput, EvidenceBundle, ToolResult


class EvidenceMapper:
    """Normalises raw connector outputs into the EvidenceBundle contract.

    Minimal in Etapa 1 — no real tool outputs exist yet.
    Extensible: add a per-connector normaliser method when Etapa 2 connectors arrive.
    """

    def build_bundle(
        self,
        assessment_id: str,
        attestations: dict[str, AttestationInput],
        tool_results: list[ToolResult] | None = None,
        red_teaming_done: bool = False,
        incident_response_plan: bool = False,
        assurance_methods_used: list[str] | None = None,
    ) -> EvidenceBundle:
        return EvidenceBundle(
            assessment_id=assessment_id,
            attestations=attestations,
            tool_results=tool_results or [],
            red_teaming_done=red_teaming_done,
            incident_response_plan=incident_response_plan,
            assurance_methods_used=assurance_methods_used or [],
        )

    def normalize_tool_result(self, raw: dict, connector: str) -> ToolResult:
        """Map a raw connector response dict to a typed ToolResult."""
        return ToolResult(
            connector=connector,
            verdict=raw.get("verdict", "unknown"),
            findings=raw.get("findings", []),
            raw_ref=raw.get("ref"),
        )
