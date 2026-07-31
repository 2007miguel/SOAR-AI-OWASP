from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ..contracts import AssessmentContext


class _Base(DeclarativeBase):
    pass


class _AssessmentRow(_Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PostgresAssessmentStore:
    """PostgreSQL-backed AssessmentStore using SQLAlchemy 2.x.

    Stores the full AssessmentContext as JSONB. The status and timestamps
    are duplicated as indexed columns for efficient querying without parsing
    the JSON payload.

    DB_URL format:
      postgresql+psycopg2://user:password@host:5432/dbname

    The table is created automatically on first instantiation if it does not exist.
    """

    def __init__(self, db_url: str) -> None:
        self._engine = create_engine(db_url, pool_pre_ping=True)
        _Base.metadata.create_all(self._engine)

    def save(self, ctx: AssessmentContext) -> None:
        with Session(self._engine) as session:
            row = _AssessmentRow(
                assessment_id=ctx.assessment_id,
                status=ctx.status.value,
                created_at=ctx.created_at,
                updated_at=ctx.updated_at,
                data=ctx.model_dump(mode="json"),
            )
            session.add(row)
            session.commit()

    def get(self, assessment_id: str) -> AssessmentContext | None:
        with Session(self._engine) as session:
            row = session.get(_AssessmentRow, assessment_id)
            if row is None:
                return None
            return AssessmentContext.model_validate(row.data)

    def update(self, ctx: AssessmentContext) -> None:
        with Session(self._engine) as session:
            row = session.get(_AssessmentRow, ctx.assessment_id)
            if row is None:
                raise KeyError(f"Assessment '{ctx.assessment_id}' not found")
            row.status = ctx.status.value
            row.updated_at = ctx.updated_at
            row.data = ctx.model_dump(mode="json")
            session.commit()
