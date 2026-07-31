#!/usr/bin/env python3
"""Stage the KB volume (kb_volume/) for the engine container.

Covers Fase 0.1 of GUIA_VALIDACION.txt: copies the canonical KB into kb_volume/
applying the documented staging normalization (observaciones/kb_volume.txt:
architecture_types[].security_practices object -> array of dicts), plus the wizard
(required for the startup flag-coverage selfcheck) and the business_context schema
(optional reference).

The canonical KB in archivos_desarrollo/ is NEVER modified; only the copy in
kb_volume/ is normalized. Re-run this script whenever the canonical KB changes.

Usage (from modulo_engine/ or anywhere):
    python scripts/stage_kb_volume.py            # stage only
    python scripts/stage_kb_volume.py --verify   # stage + confirm it will boot
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
_ENGINE_DIR = _SCRIPT.parent.parent            # modulo_engine/
_REPO_ROOT = _ENGINE_DIR.parent                # SOAR-AI-OWASP/

_SRC_KB = _REPO_ROOT / "archivos_desarrollo" / "knoledge_base_sistema" / "owasp_asi_knowledge_base.json"
_SRC_WIZARD = _REPO_ROOT / "archivos_desarrollo" / "Entradas_del_sistema" / "wizard" / "agent_validation_wizard.json"
_SRC_BCTX = _REPO_ROOT / "archivos_desarrollo" / "Entradas_del_sistema" / "business_context" / "agent_business_context.json"

_DEST_DIR = _ENGINE_DIR / "kb_volume"

_REQUIRED_SECTIONS = [
    "metadata", "capability_taxonomy", "threat_catalog", "controls_catalog",
    "assurance_methods", "architecture_types", "operational_capabilities",
    "verdict_framework",
]


def _normalize_security_practices(data: dict) -> int:
    """architecture_types[].security_practices: object -> array of dicts. Idempotent.
    Returns how many arch types were normalized (0 if already staged)."""
    changed = 0
    for t in data.get("architecture_types", {}).get("types", []):
        sp = t.get("security_practices")
        if isinstance(sp, dict):
            t["security_practices"] = [dict(domain=k, **v) for k, v in sp.items()]
            changed += 1
    return changed


def stage() -> None:
    if not _SRC_KB.exists():
        sys.exit(f"ERROR: canonical KB not found at {_SRC_KB}")

    _DEST_DIR.mkdir(parents=True, exist_ok=True)

    # --- KB: load, check structure, normalize, write ---
    data = json.loads(_SRC_KB.read_text(encoding="utf-8"))
    missing = [s for s in _REQUIRED_SECTIONS if s not in data]
    if missing:
        sys.exit(f"ERROR: canonical KB is missing required sections: {missing}")

    normalized = _normalize_security_practices(data)
    dest_kb = _DEST_DIR / "owasp_asi_knowledge_base.json"
    dest_kb.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK]   KB staged        -> {dest_kb}")
    print(f"       security_practices normalized (object->array) in {normalized} architecture type(s)")

    # --- Wizard (required: startup flag-coverage selfcheck) ---
    if _SRC_WIZARD.exists():
        shutil.copyfile(_SRC_WIZARD, _DEST_DIR / _SRC_WIZARD.name)
        print(f"[OK]   Wizard staged    -> {_DEST_DIR / _SRC_WIZARD.name}")
    else:
        print(f"[WARN] Wizard not found at {_SRC_WIZARD}")
        print("       REQUIRED: the engine will not start without it.")

    # --- business_context schema (optional reference) ---
    if _SRC_BCTX.exists():
        shutil.copyfile(_SRC_BCTX, _DEST_DIR / _SRC_BCTX.name)
        print(f"[OK]   business_context -> {_DEST_DIR / _SRC_BCTX.name}")
    else:
        print("[--]   business_context schema not found (optional) — skipped")

    print(f"\nVolume ready at: {_DEST_DIR}")
    print("In .env set:     KB_PATH=/app/kb/owasp_asi_knowledge_base.json")
    print("docker-compose mounts it as:  ./kb_volume:/app/kb:ro")


def verify() -> None:
    """Optional: run the engine's own startup checks against the staged volume."""
    sys.path.insert(0, str(_ENGINE_DIR / "src"))
    try:
        from validation_engine.kb import check_volume, load, load_wizard_flags, selfcheck
        from validation_engine.kb.loader import KBVolumeError
        from validation_engine.kb.selfcheck import KBSelfCheckError
    except ImportError as exc:
        print(f"[SKIP] verification skipped (engine deps not importable: {exc})")
        print("       install deps to enable:  pip install -e .")
        return

    try:
        check_volume(_DEST_DIR)
        kb = load(_DEST_DIR / "owasp_asi_knowledge_base.json")
        flags = load_wizard_flags(_DEST_DIR)
        selfcheck(kb, flags)
    except (KBVolumeError, KBSelfCheckError) as exc:
        sys.exit(f"[FAIL] staged volume did not pass startup checks:\n{exc}")

    print(f"[OK]   staged volume passes check_volume + load + selfcheck")
    print(f"       KB version = {kb.metadata.version} — the container will boot with this volume")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage kb_volume/ for the engine container.")
    parser.add_argument(
        "--verify", action="store_true",
        help="After staging, run the engine's startup checks to confirm it will boot.",
    )
    args = parser.parse_args()
    stage()
    if args.verify:
        print()
        verify()


if __name__ == "__main__":
    main()
