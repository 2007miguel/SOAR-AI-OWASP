from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from .attestation.intake import AttestationIntake
from .attestation.partial_store import PartialStore
from .checklist.presenter import ChecklistPresenter
from .config import Settings
from .connectors.registry import ConnectorRegistry
from .connectors.selector import ConnectorSelector
from .log_setup import configure as configure_logging
from .persistence.job_store import JobStore
from .port.assurance_api import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = Settings()
    configure_logging(settings.log_level)

    store = JobStore(settings.db_url)
    registry = ConnectorRegistry()

    app.state.store = store
    app.state.intake = AttestationIntake(store)
    app.state.partial_store = PartialStore(store)
    app.state.presenter = ChecklistPresenter()
    app.state.selector = ConnectorSelector(registry)
    app.state.engine_url = settings.engine_url.rstrip("/")

    logger.info("Assurance coordinator ready — engine_url=%s", app.state.engine_url)
    yield


app = FastAPI(
    title="SOAR-AI Assurance Coordinator",
    description="M6: HITL attestation tracking and (future) connector orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
