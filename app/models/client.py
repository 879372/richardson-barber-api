import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(150))
    phone: Mapped[str] = mapped_column(sa.String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    birthday: Mapped[datetime | None] = mapped_column(sa.Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    total_spent: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0)
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
        "Schedule", back_populates="client"
    )
