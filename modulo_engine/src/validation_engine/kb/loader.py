from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import KnowledgeBase

_log = logging.getLogger(__name__)

# Files the engine expects in the volume directory.
# (name, required)  — required=True blocks startup if missing.
_WIZARD_FILENAME = "agent_validation_wizard.json"
_VOLUME_FILES: list[tuple[str, bool]] = [
    ("owasp_asi_knowledge_base.json", True),
    (_WIZARD_FILENAME,                True),   # required: startup flag-coverage selfcheck (wizard vs KB)
    ("agent_business_context.json",   False),
]

# Top-level sections the KB JSON must contain.
_REQUIRED_KB_SECTIONS = [
    "metadata",
    "capability_taxonomy",
    "threat_catalog",
    "controls_catalog",
    "assurance_methods",
    "architecture_types",
    "operational_capabilities",
    "verdict_framework",
]


class KBVolumeError(Exception):
    pass


def check_volume(kb_dir: str | Path) -> None:
    """Verify the volume directory and its expected files exist before loading.

    Logs every check so the operator can see exactly what was found or missing.
    Raises KBVolumeError if any required file is absent.
    """
    kb_dir = Path(kb_dir)
    _log.info("KB volume check — directory: %s", kb_dir)

    if not kb_dir.exists():
        raise KBVolumeError(
            f"KB volume directory not found: {kb_dir}\n"
            "  → Is the Docker volume mounted? Check docker-compose.yml and KB_PATH."
        )
    if not kb_dir.is_dir():
        raise KBVolumeError(f"KB_PATH parent is not a directory: {kb_dir}")

    missing_required: list[str] = []

    for filename, required in _VOLUME_FILES:
        file_path = kb_dir / filename
        label = "REQUIRED" if required else "optional"
        if file_path.exists():
            _log.info("  [OK]      %-45s (%s)", filename, label)
        else:
            if required:
                _log.error("  [MISSING] %-45s (%s)", filename, label)
                missing_required.append(filename)
            else:
                _log.warning("  [ABSENT]  %-45s (%s — selfcheck limited)", filename, label)

    if missing_required:
        files = ", ".join(missing_required)
        raise KBVolumeError(
            f"KB volume is missing required file(s): {files}\n"
            f"  → Expected location: {kb_dir}\n"
            f"  → See kb_volume/README.txt for the expected volume structure."
        )

    _log.info("KB volume check passed.")


def load(path: str | Path) -> KnowledgeBase:
    """Load and validate the knowledge base JSON from disk.

    Call check_volume() before this to catch structural problems early.
    """
    path = Path(path)
    _log.info("Loading KB from %s", path)

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise KBVolumeError(
            f"KB file is not valid JSON: {path}\n  → {exc}"
        ) from exc

    _check_required_sections(data, path)

    kb = KnowledgeBase.model_validate(data)
    _inject_lifecycle_phases(kb)

    _log.info(
        "KB loaded — version=%s  threats=%d  controls=%d  steps=%d",
        kb.metadata.version,
        len(kb.threat_catalog.threats),
        sum(len(d.controls) for d in kb.controls_catalog.domains),
        len(kb.capability_taxonomy.steps),
    )
    return kb


def load_wizard_flags(kb_dir: str | Path) -> set[str]:
    """Return the set of capability_flags declared in the wizard coverage map.

    Used by selfcheck to verify wizard↔KB flag coverage at startup
    (arquitectura_sistema.txt §8; estructura_engine.txt §2/§3).
    """
    path = Path(kb_dir) / _WIZARD_FILENAME
    _log.info("Loading wizard coverage map from %s", path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise KBVolumeError(
            f"Wizard file is not valid JSON: {path}\n  → {exc}"
        ) from exc

    flag_map = data.get("coverage_validation", {}).get("flag_coverage_map", {})
    if not flag_map:
        raise KBVolumeError(
            f"Wizard file {path} has no coverage_validation.flag_coverage_map; "
            "cannot run the flag-coverage selfcheck."
        )
    return set(flag_map.keys())


def _check_required_sections(data: dict, path: Path) -> None:
    missing = [s for s in _REQUIRED_KB_SECTIONS if s not in data]
    if missing:
        raise KBVolumeError(
            f"KB JSON at {path} is missing required top-level section(s): {missing}\n"
            f"  → See kb_volume/README.txt for the expected JSON structure."
        )


def _inject_lifecycle_phases(kb: KnowledgeBase) -> None:
    """Copy domain-level lifecycle_phases into each Control (phases live on domain, not control)."""
    for domain in kb.controls_catalog.domains:
        for control in domain.controls:
            control.lifecycle_phases = domain.applicable_lifecycle_phases
