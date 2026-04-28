import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WeekDay(int, Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Availability(Base):
    """Defines working hours per barber per weekday."""

    __tablename__ = "availabilities"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True
    )
    week_day: Mapped[WeekDay] = mapped_column(sa.Integer)
    start_time: Mapped[str] = mapped_column(sa.String(5))   # "HH:MM"
    end_time: Mapped[str] = mapped_column(sa.String(5))     # "HH:MM"
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    # Relationships
    barber: Mapped["User"] = relationship("User", back_populates="availabilities")  # noqa: F821


class TimeBlock(Base):
    """Manual blocks: vacation, holidays, personal commitments."""

    __tablename__ = "time_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuditLog(Base):
    """Tracks all significant user actions for auditing."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True
    )
    action: Mapped[str] = mapped_column(sa.String(100))
    resource: Mapped[str] = mapped_column(sa.String(100))
    resource_id: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")  # noqa: F821
