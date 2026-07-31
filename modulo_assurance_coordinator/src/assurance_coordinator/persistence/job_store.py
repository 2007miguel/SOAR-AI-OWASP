from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.orm.attributes import flag_modified

from ..contracts.jobs import ConnectorJob, JobStatus


class _Base(DeclarativeBase):
    pass


class _SessionRow(_Base):
    __tablename__ = "coordinator_sessions"

    assessment_id: Mapped[str] = mapped_column(String, primary_key=True)
    active_asi: Mapped[list] = mapped_column(JSONB, nullable=False)
    checklist: Mapped[list] = mapped_column(JSONB, nullable=False)
    attestations: Mapped[dict] = mapped_column(JSONB, nullable=False)
    incident_response_plan: Mapped[bool] = mapped_column(Boolean, nullable=False)
    red_teaming_done: Mapped[bool] = mapped_column(Boolean, nullable=False)
    red_teaming_critical_findings: Mapped[bool] = mapped_column(Boolean, nullable=False)
    supply_chain_unverified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    production_access: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assurance_methods_used: Mapped[list] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class _ConnectorJobRow(_Base):
    __tablename__ = "connector_jobs"

    job_id: Mapped[str] = mapped_column(String, primary_key=True)
    assessment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    connector: Mapped[str] = mapped_column(String, nullable=False)
    assur_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@dataclass
class SessionData:
    assessment_id: str
    active_asi: list
    checklist: list
    attestations: dict
    incident_response_plan: bool
    red_teaming_done: bool
    red_teaming_critical_findings: bool
    supply_chain_unverified: bool
    production_access: bool
    assurance_methods_used: list
    status: str
    created_at: datetime
    updated_at: datetime


class JobStore:
    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url, pool_pre_ping=True)
        _Base.metadata.create_all(self._engine)

    # ── Session management ──────────────────────────────────────────────────

    def create_session(
        self,
        assessment_id: str,
        active_asi: list[str],
        checklist: list[dict],
    ) -> None:
        now = datetime.now(timezone.utc)
        with Session(self._engine) as session:
            row = _SessionRow(
                assessment_id=assessment_id,
                active_asi=active_asi,
                checklist=checklist,
                attestations={},
                incident_response_plan=False,
                red_teaming_done=False,
                red_teaming_critical_findings=False,
                supply_chain_unverified=False,
                production_access=False,
                assurance_methods_used=[],
                status="pending",
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.commit()

    def get_session(self, assessment_id: str) -> SessionData | None:
        with Session(self._engine) as session:
            row = session.get(_SessionRow, assessment_id)
            if row is None:
                return None
            return SessionData(
                assessment_id=row.assessment_id,
                active_asi=row.active_asi or [],
                checklist=row.checklist or [],
                attestations=row.attestations or {},
                incident_response_plan=row.incident_response_plan,
                red_teaming_done=row.red_teaming_done,
                red_teaming_critical_findings=row.red_teaming_critical_findings,
                supply_chain_unverified=row.supply_chain_unverified,
                production_access=row.production_access,
                assurance_methods_used=row.assurance_methods_used or [],
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def update_attestations(
        self,
        assessment_id: str,
        new_attestations: dict,
        **flags: object,
    ) -> None:
        with Session(self._engine) as session:
            row = session.get(_SessionRow, assessment_id)
            if row is None:
                raise KeyError(f"No coordinator session for '{assessment_id}'")

            row.attestations = {**(row.attestations or {}), **new_attestations}
            flag_modified(row, "attestations")

            for key, val in flags.items():
                if val is None or not hasattr(row, key):
                    continue
                if key == "assurance_methods_used":
                    existing = set(row.assurance_methods_used or [])
                    row.assurance_methods_used = sorted(existing | set(val))  # type: ignore[arg-type]
                    flag_modified(row, "assurance_methods_used")
                else:
                    setattr(row, key, val)

            row.updated_at = datetime.now(timezone.utc)
            session.commit()

    def is_ready(self, assessment_id: str) -> bool:
        with Session(self._engine) as session:
            row = session.get(_SessionRow, assessment_id)
            if row is None:
                return False
            critical_ids = {item["control_id"] for item in (row.checklist or [])}
            return critical_ids.issubset(set((row.attestations or {}).keys()))

    def mark_ready(self, assessment_id: str) -> None:
        with Session(self._engine) as session:
            row = session.get(_SessionRow, assessment_id)
            if row is None:
                raise KeyError(f"No coordinator session for '{assessment_id}'")
            row.status = "ready"
            row.updated_at = datetime.now(timezone.utc)
            session.commit()

    # ── Connector jobs ──────────────────────────────────────────────────────

    def create_job(self, job: ConnectorJob) -> None:
        with Session(self._engine) as session:
            row = _ConnectorJobRow(
                job_id=job.job_id,
                assessment_id=job.assessment_id,
                connector=job.connector,
                assur_id=job.assur_id,
                status=job.status.value,
                result=None,
                created_at=job.created_at,
                completed_at=None,
            )
            session.add(row)
            session.commit()

    def update_job(
        self,
        job_id: str,
        status: JobStatus,
        result: dict | None = None,
    ) -> None:
        with Session(self._engine) as session:
            row = session.get(_ConnectorJobRow, job_id)
            if row is None:
                raise KeyError(f"Connector job '{job_id}' not found")
            row.status = status.value
            row.result = result
            row.completed_at = datetime.now(timezone.utc)
            session.commit()
