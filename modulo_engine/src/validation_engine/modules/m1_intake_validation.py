from __future__ import annotations

from ..contracts import AssessmentContext
from ..contracts.analysis import ValidationResult
from ..contracts.enums import ArchitectureId, Status
from ..kb.service import KBService


class M1IntakeValidation:
    name = "m1_intake_validation"
    reads = ["inputs.capability_flags", "inputs.business_context", "inputs.aibom"]
    writes = ["analysis.validation", "analysis.warnings", "status"]

    def run(self, ctx: AssessmentContext, kb: KBService) -> AssessmentContext:
        errors: list[dict] = []
        warnings: list[dict] = []

        # 1.1 lifecycle_phases must not be empty (field is required but list could be [])
        if not ctx.inputs.business_context.lifecycle_phases:
            errors.append({
                "code": "LIFECYCLE_PHASES_EMPTY",
                "message": "business_context.lifecycle_phases must contain at least one phase (design, build, runtime)",
            })

        # 1.3 Cross-input: multi-agent architecture_id must match multi_agent_architecture flag
        arch = ctx.inputs.business_context.architecture_id
        flags = ctx.inputs.capability_flags

        if arch in (ArchitectureId.CENTRAL, ArchitectureId.SWARM) and not flags.multi_agent_architecture:
            warnings.append({
                "code": "ARCH_FLAG_MISMATCH",
                "message": (
                    f"architecture_id is {arch.value} but capability_flags.multi_agent_architecture is false. "
                    "Declare multi_agent_architecture=true in the wizard or review the architecture selection."
                ),
            })

        if flags.multi_agent_architecture and arch == ArchitectureId.SINGLE:
            warnings.append({
                "code": "FLAG_ARCH_MISMATCH",
                "message": (
                    "capability_flags.multi_agent_architecture is true but architecture_id is ARCH-SINGLE. "
                    "Consider ARCH-CENTRAL or ARCH-SWARM."
                ),
            })

        # 1.4 AIBOM: informative in v1 — flag if absent so the report notes it
        if ctx.inputs.aibom is None:
            warnings.append({
                "code": "AIBOM_ABSENT",
                "message": (
                    "No AI-BOM provided. CTRL-SC-01 attestation will require manual evidence. "
                    "supply_chain_dependencies and dataset sensitiveData signals unavailable."
                ),
            })

        ok = len(errors) == 0
        ctx.analysis.validation = ValidationResult(ok=ok, errors=errors)
        ctx.analysis.warnings = warnings
        ctx.status = Status.ANALYZING if ok else Status.ERROR

        return ctx
