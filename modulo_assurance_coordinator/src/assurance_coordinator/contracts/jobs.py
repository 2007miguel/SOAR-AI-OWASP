from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from .evidence import ToolResult


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConnectorJob(BaseModel):
    job_id: str
    assessment_id: str
    connector: str     # e.g. "connector-promptfoo"
    assur_id: str      # ASSUR-01, ASSUR-05, …
    status: JobStatus = JobStatus.PENDING
    result: ToolResult | None = None
    created_at: datetime
    completed_at: datetime | None = None
