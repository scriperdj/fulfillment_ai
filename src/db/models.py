"""SQLAlchemy ORM models for the fulfillment AI system.

FK chain: batch_jobs → predictions → deviations → agent_responses
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    JSON as SA_JSON,
)
from sqlalchemy import (
    UUID as SA_UUID,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    dag_run_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="batch_job", cascade="all, delete-orphan"
    )
    deviations: Mapped[list["Deviation"]] = relationship(
        back_populates="batch_job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_batch_jobs_status", "status"),
        Index("ix_batch_jobs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BatchJob(id={self.id}, status={self.status!r}, rows={self.row_count})>"


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    batch_job_id: Mapped[uuid.UUID | None] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("batch_jobs.id"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    delay_probability: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    features_json: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    batch_job: Mapped[BatchJob | None] = relationship(back_populates="predictions")
    deviations: Mapped[list["Deviation"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_predictions_batch_job_id", "batch_job_id"),
        Index("ix_predictions_order_id", "order_id"),
        Index("ix_predictions_severity", "severity"),
        Index("ix_predictions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Prediction(id={self.id}, order={self.order_id!r}, p={self.delay_probability:.2f})>"


class Deviation(Base):
    __tablename__ = "deviations"

    id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("predictions.id"),
        nullable=False,
    )
    batch_job_id: Mapped[uuid.UUID | None] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("batch_jobs.id"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    prediction: Mapped[Prediction] = relationship(back_populates="deviations")
    batch_job: Mapped[BatchJob | None] = relationship(back_populates="deviations")
    agent_responses: Mapped[list["AgentResponse"]] = relationship(
        back_populates="deviation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_deviations_prediction_id", "prediction_id"),
        Index("ix_deviations_batch_job_id", "batch_job_id"),
        Index("ix_deviations_severity", "severity"),
        Index("ix_deviations_status", "status"),
        Index("ix_deviations_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Deviation(id={self.id}, severity={self.severity!r}, status={self.status!r})>"


class AgentResponse(Base):
    __tablename__ = "agent_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True), primary_key=True, default=_new_uuid
    )
    deviation_id: Mapped[uuid.UUID] = mapped_column(
        SA_UUID(as_uuid=True),
        ForeignKey("deviations.id"),
        nullable=False,
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(200), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(SA_JSON, nullable=True)
    conversation_history: Mapped[list | None] = mapped_column(SA_JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    deviation: Mapped[Deviation] = relationship(back_populates="agent_responses")

    __table_args__ = (
        Index("ix_agent_responses_deviation_id", "deviation_id"),
        Index("ix_agent_responses_agent_type", "agent_type"),
        Index("ix_agent_responses_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentResponse(id={self.id}, type={self.agent_type!r}, action={self.action!r})>"
