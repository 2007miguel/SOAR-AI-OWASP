from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .config import Settings
from .log_setup import configure as configure_logging
from .kb import (
    KBSelfCheckError,
    KBVolumeError,
    KBService,
    check_volume,
    load,
    load_wizard_flags,
    selfcheck,
)
from .orchestrator import Orchestrator, load_playbook
from .assurance import ManualAdapter
from .persistence import PostgresAssessmentStore
from .api import router

logger = logging.getLogger(__name__)

_PLAYBOOK_PATH = Path(__file__).parent / "orchestrator" / "playbooks" / "full_validation.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings.log_level)

    # ── KB startup sequence ───────────────────────────────────────────────────
    try:
        kb_dir = Path(settings.kb_path).parent
        check_volume(kb_dir)
        kb = load(settings.kb_path)
        wizard_flags = load_wizard_flags(kb_dir)
        selfcheck(kb, wizard_flags)
    except (KBVolumeError, KBSelfCheckError) as exc:
        logger.critical("KB startup failed — %s", exc)
        raise SystemExit(1) from exc

    kb_service = KBService(kb)
    logger.info("KB loaded — version %s", kb_service.kb_version())

    # ── Build services ────────────────────────────────────────────────────────
    playbook = load_playbook(_PLAYBOOK_PATH)
    assurance = ManualAdapter(kb_service)
    orchestrator = Orchestrator(playbook, kb_service, assurance)
    store = PostgresAssessmentStore(settings.db_url)

    app.state.kb = kb_service
    app.state.orchestrator = orchestrator
    app.state.store = store
    app.state.assurance = assurance

    logger.info("Engine ready — playbook '%s'", playbook.id)
    yield


app = FastAPI(
    title="SOAR-AI OWASP Engine",
    description="Prescriptive OWASP compliance engine for AI agents.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
