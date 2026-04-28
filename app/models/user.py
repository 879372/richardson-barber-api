import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    BARBER = "barber"
    RECEPTIONIST = "receptionist"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(150))
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(sa.String(255))
    role: Mapped[UserRole] = mapped_column(sa.Enum(UserRole), default=UserRole.BARBER)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    schedules: Mapped[list["Schedule"]] = relationship(  # noqa: F821
        "Schedule", back_populates="barber", foreign_keys="Schedule.barber_id"
    )
    availabilities: Mapped[list["Availability"]] = relationship(  # noqa: F821
        "Availability", back_populates="barber"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(  # noqa: F821
        "AuditLog", back_populates="user"
    )
