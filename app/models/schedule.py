import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScheduleStatus(str, Enum):
    PENDING = "pending"            # Aguardando confirmação
    CONFIRMED = "confirmed"        # Confirmado
    COMPLETED = "completed"        # Concluído
    CANCELLED = "cancelled"        # Cancelado
    NO_SHOW = "no_show"            # Não compareceu


class PaymentMethod(str, Enum):
    PIX = "pix"
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    TRANSFER = "transfer"


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("clients.id"), index=True
    )
    barber_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("services.id")
    )
    scheduled_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    status: Mapped[ScheduleStatus] = mapped_column(
        sa.Enum(ScheduleStatus), default=ScheduleStatus.PENDING, index=True
    )
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    total_price: Mapped[float] = mapped_column(sa.Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="schedules")  # noqa: F821
    barber: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="schedules", foreign_keys=[barber_id]
    )
    service: Mapped["Service"] = relationship("Service", back_populates="schedules")  # noqa: F821
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        "Payment", back_populates="schedule", cascade="all, delete-orphan"
    )
    whatsapp_logs: Mapped[list["WhatsAppLog"]] = relationship(  # noqa: F821
        "WhatsAppLog", back_populates="schedule"
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("schedules.id"), index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(sa.Enum(PaymentMethod))
    amount: Mapped[float] = mapped_column(sa.Numeric(10, 2))
    paid_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    schedule: Mapped["Schedule"] = relationship("Schedule", back_populates="payments")
