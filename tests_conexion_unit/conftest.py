"""Root conftest for tests_conexion.

Adds both engine and coordinator src/ directories to sys.path so that
`validation_engine` and `assurance_coordinator` are importable without a
pip install. No Docker or real Postgres is needed — all tests use in-memory
fakes and respx HTTP mocks.

To run:
    pip install -r requirements.txt   # from this directory
    pytest
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).parent
_ROOT = _HERE.parent  # SOAR-AI-OWASP/

sys.path.insert(0, str(_ROOT / "modulo_engine" / "src"))
sys.path.insert(0, str(_ROOT / "modulo_assurance_coordinator" / "src"))
