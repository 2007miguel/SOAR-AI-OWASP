"""Builders for example inputs used across the golden tests.

Kept as plain factory functions so any test can construct an AssessmentContext or
its parts without depending on the orchestrator or the API layer.
"""
from __future__ import annotations

from validation_engine.contracts import AssessmentContext
from validation_engine.contracts.inputs import Aibom, BusinessContext, CapabilityFlags, InputsLayer
from validation_engine.contracts.enums import ArchitectureId, BusinessDomain, LifecyclePhase


def flags(**active: bool) -> CapabilityFlags:
    """CapabilityFlags with the named flags set True, the rest False."""
    return CapabilityFlags(**active)


def business_context(
    domain: BusinessDomain = BusinessDomain.TECHNOLOGY,
    arch: ArchitectureId = ArchitectureId.SINGLE,
    phases: list[LifecyclePhase] | None = None,
) -> BusinessContext:
    return BusinessContext(
        business_domain=domain,
        architecture_id=arch,
        lifecycle_phases=phases if phases is not None else [LifecyclePhase.RUNTIME],
    )


def context(
    kb_version: str = "1.0",
    capability_flags: CapabilityFlags | None = None,
    domain: BusinessDomain = BusinessDomain.TECHNOLOGY,
    arch: ArchitectureId = ArchitectureId.SINGLE,
    phases: list[LifecyclePhase] | None = None,
    aibom: Aibom | None = None,
) -> AssessmentContext:
    return AssessmentContext(
        kb_version=kb_version,
        playbook_id="",
        inputs=InputsLayer(
            capability_flags=capability_flags or CapabilityFlags(),
            business_context=business_context(domain, arch, phases),
            aibom=aibom,
        ),
    )
