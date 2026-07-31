"""Shared pytest fixtures for the engine test suite.

The tests only COUPLE onto the engine: they import and exercise src/ code, never
modify it. The knowledge base used is the real OWASP KB developed for the system
(archivos_desarrollo/), staged exactly as the deployment volume would stage it
(kb_volume.txt normalization), so the golden tests lock fidelity to that KB.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_ENGINE_DIR = _TESTS_DIR.parent
_REPO_ROOT = _ENGINE_DIR.parent

# Make src/ (the package) and tests/ (the fixtures package) importable without
# installing the engine. Runs before test modules are collected.
sys.path.insert(0, str(_ENGINE_DIR / "src"))
sys.path.insert(0, str(_TESTS_DIR))

from validation_engine.kb import KBService  # noqa: E402
from validation_engine.kb.models import KnowledgeBase  # noqa: E402
from validation_engine.kb.loader import _inject_lifecycle_phases  # noqa: E402
from validation_engine.orchestrator import Orchestrator, load_playbook  # noqa: E402
from validation_engine.assurance import ManualAdapter  # noqa: E402

_KB_PATH = _REPO_ROOT / "archivos_desarrollo" / "knoledge_base_sistema" / "owasp_asi_knowledge_base.json"
_WIZARD_PATH = _REPO_ROOT / "archivos_desarrollo" / "Entradas_del_sistema" / "wizard" / "agent_validation_wizard.json"
_PLAYBOOK_PATH = _ENGINE_DIR / "src" / "validation_engine" / "orchestrator" / "playbooks" / "full_validation.yaml"


def _stage_kb_data(data: dict) -> dict:
    """Apply the documented volume staging normalization (kb_volume.txt):
    architecture_types[].security_practices object -> array of dicts."""
    for t in data.get("architecture_types", {}).get("types", []):
        sp = t.get("security_practices")
        if isinstance(sp, dict):
            t["security_practices"] = [dict(domain=k, **v) for k, v in sp.items()]
    return data


@pytest.fixture(scope="session")
def raw_kb() -> KnowledgeBase:
    """The real KB, staged in-memory (kb_volume.txt normalization) and validated with
    the engine's own models + lifecycle injection (same steps as loader.load)."""
    if not _KB_PATH.exists():
        pytest.skip(f"Real KB not found at {_KB_PATH}")
    data = _stage_kb_data(json.loads(_KB_PATH.read_text(encoding="utf-8")))
    kb = KnowledgeBase.model_validate(data)
    _inject_lifecycle_phases(kb)
    return kb


@pytest.fixture(scope="session")
def kb(raw_kb) -> KBService:
    return KBService(raw_kb)


@pytest.fixture(scope="session")
def wizard_flags() -> set[str]:
    if not _WIZARD_PATH.exists():
        pytest.skip(f"Wizard not found at {_WIZARD_PATH}")
    data = json.loads(_WIZARD_PATH.read_text(encoding="utf-8"))
    return set(data["coverage_validation"]["flag_coverage_map"].keys())


@pytest.fixture(scope="session")
def orchestrator(kb) -> Orchestrator:
    return Orchestrator(load_playbook(_PLAYBOOK_PATH), kb, ManualAdapter(kb))
