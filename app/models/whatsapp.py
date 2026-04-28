import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WhatsAppMessageType(str, Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    REMINDER_24H = "reminder_24h"
    REMINDER_1H = "reminder_1h"
    POST_SERVICE = "post_service"
    CUSTOM = "custom"


class WhatsAppStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"
    PENDING = "pending"


class WhatsAppLog(Base):
    __tablename__ = "whatsapp_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("schedules.id"), nullable=True, index=True
    )
    recipient_phone: Mapped[str] = mapped_column(sa.String(20))
    message_type: Mapped[WhatsAppMessageType] = mapped_column(sa.Enum(WhatsAppMessageType))
    message_body: Mapped[str] = mapped_column(sa.Text)
    status: Mapped[WhatsAppStatus] = mapped_column(
        sa.Enum(WhatsAppStatus), default=WhatsAppStatus.PENDING
    )
    error_detail: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    schedule: Mapped["Schedule"] = relationship(  # noqa: F821
        "Schedule", back_populates="whatsapp_logs"
    )


class WhatsAppTemplate(Base):
    """Configurable message templates for each trigger type."""

    __tablename__ = "whatsapp_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_type: Mapped[WhatsAppMessageType] = mapped_column(
        sa.Enum(WhatsAppMessageType), unique=True
    )
    template_text: Mapped[str] = mapped_column(sa.Text)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
