from __future__ import annotations

from ..contracts.checklist import ChecklistBundle, ChecklistItem


class ChecklistPresenter:
    """Internal helper: formats and categorises checklist items.

    Never exposed as a public endpoint — the frontend always talks to the engine.
    Used by the coordinator to decide which items go to HITL vs automated connectors.
    """

    def hitl_items(self, bundle: ChecklistBundle) -> list[ChecklistItem]:
        """Items that require human attestation.
        In Etapa 1 this is every item (no automated connectors registered)."""
        return bundle.items

    def tool_items(self, bundle: ChecklistBundle) -> list[ChecklistItem]:
        """Items coverable by automated connectors. Empty in Etapa 1."""
        return []

    def summary(self, bundle: ChecklistBundle) -> list[dict]:
        """Format checklist for logging and internal tracking."""
        return [
            {
                "control_id": item.control_id,
                "category": item.category,
                "why": item.why,
                "suggested_assur": item.suggested_assur,
                "needs_tool": bool(item.suggested_assur),
            }
            for item in bundle.items
        ]
